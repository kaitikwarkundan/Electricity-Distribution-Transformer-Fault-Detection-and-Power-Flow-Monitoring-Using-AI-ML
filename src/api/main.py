"""
src/api/main.py — FastAPI application entry point.

Startup sequence:
  1. Init SQLite DB + seed transformer fleet
  2. Load ML models
  3. Start simulation orchestrator (12 background threads)
  4. Register packet callback → ML inference → DB write → alert engine

Run: uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import FAULT_CLASSES, FAULT_SEVERITY, RUL_CRITICAL_DAYS, RUL_WARNING_DAYS
from src.database.init_db import init_db, get_session
from src.database.models import Telemetry, Alert, WorkOrder, Transformer, RULPrediction
from src.simulator.orchestrator import orchestrator, register_packet_callback
from src.ml.inference import load_models, run_inference
from src.api.routes import fleet, alerts, work_orders, rul as rul_routes

log = logging.getLogger("dtms.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

# ─── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()

# ─── Packet processing pipeline ───────────────────────────────────────────────

RUL_WRITE_INTERVAL = 30    # write RUL prediction every 30 packets per transformer
_rul_counters: dict[str, int] = {}

# Deduplication: don't create duplicate alerts within 60 seconds
_last_alert_ts: dict[str, datetime] = {}
ALERT_DEBOUNCE_SEC = 60


def _process_packet(pkt: dict):
    """
    Called from simulation worker thread for every new telemetry packet.
    1. Run ML inference
    2. Write telemetry + inference results to DB
    3. Create alert if fault detected
    4. Auto-create work order for CRITICAL / HIGH alerts
    5. Write RUL prediction every N packets
    6. Broadcast to WebSocket clients (via event loop)
    """
    tid = pkt["transformer_id"]

    # ── ML Inference ──────────────────────────────────────────────────────────
    result = run_inference(pkt)
    pkt.update(result)   # merge inference results into packet

    session = get_session()
    try:
        ts = datetime.fromisoformat(pkt["timestamp"])

        # ── Write telemetry ───────────────────────────────────────────────────
        tel = Telemetry(
            transformer_id  = tid,
            timestamp       = ts,
            va=pkt.get("va"), vb=pkt.get("vb"), vc=pkt.get("vc"),
            ia=pkt.get("ia"), ib=pkt.get("ib"), ic=pkt.get("ic"),
            oil_temp        = pkt.get("oil_temp"),
            power_factor    = pkt.get("power_factor"),
            active_power    = pkt.get("active_power"),
            reactive_power  = pkt.get("reactive_power"),
            loading_pct     = pkt.get("loading_pct"),
            thd             = pkt.get("thd"),
            vuf             = pkt.get("vuf"),
            h2_ppm          = pkt.get("h2_ppm"),
            i2t_acc         = pkt.get("i2t_acc"),
            dv_dt           = pkt.get("dv_dt"),
            di_dt           = pkt.get("di_dt"),
            dt_dt           = pkt.get("dt_dt"),
            v_avg           = pkt.get("v_avg"),
            i_avg           = pkt.get("i_avg"),
            v_unbalance     = pkt.get("v_unbalance"),
            i_unbalance     = pkt.get("i_unbalance"),
            anomaly_score   = result.get("anomaly_score"),
            fault_class     = result.get("fault_class"),
            fault_confidence= result.get("fault_confidence"),
            fault_label     = pkt.get("fault_label", 0),
        )
        session.add(tel)

        # ── Update transformer status ─────────────────────────────────────────
        fault_class = result.get("fault_class", 0)
        severity    = result.get("fault_severity", "NORMAL")
        tr = session.query(Transformer).filter_by(id=tid).first()
        if tr:
            status_map = {
                "NORMAL": "NORMAL", "LOW": "WARNING",
                "MEDIUM": "WARNING", "HIGH": "FAULT", "CRITICAL": "CRITICAL",
            }
            tr.status = status_map.get(severity, "NORMAL")

        # ── Create alert (debounced, non-normal only) ─────────────────────────
        if fault_class != 0 and result.get("fault_confidence", 0) > 0.65:
            last = _last_alert_ts.get(tid)
            now  = datetime.now()
            if last is None or (now - last).total_seconds() > ALERT_DEBOUNCE_SEC:
                _last_alert_ts[tid] = now
                msg = (
                    f"{FAULT_CLASSES[fault_class]} detected on {tid}. "
                    f"Confidence: {result['fault_confidence']:.1%}. "
                    f"Loading: {pkt.get('loading_pct', 0):.1f}%  "
                    f"Oil Temp: {pkt.get('oil_temp', 0):.1f}°C"
                )
                alert = Alert(
                    transformer_id = tid,
                    timestamp      = ts,
                    severity       = severity,
                    fault_type     = FAULT_CLASSES[fault_class],
                    fault_class    = fault_class,
                    confidence     = result.get("fault_confidence"),
                    message        = msg,
                    acknowledged   = False,
                )
                session.add(alert)
                session.flush()   # get alert.id

                # Auto-create work order for HIGH / CRITICAL faults
                if severity in ("HIGH", "CRITICAL"):
                    wo = WorkOrder(
                        transformer_id = tid,
                        alert_id       = alert.id,
                        title          = f"[AUTO] {FAULT_CLASSES[fault_class]} — {tid}",
                        description    = msg,
                        priority       = severity,
                        status         = "OPEN",
                        created_at     = now,
                    )
                    session.add(wo)

        # ── RUL prediction (every N packets) ─────────────────────────────────
        _rul_counters[tid] = _rul_counters.get(tid, 0) + 1
        if _rul_counters[tid] % RUL_WRITE_INTERVAL == 0:
            ins = result.get("insulation_rul_days")
            oil = result.get("oil_rul_days")
            wnd = result.get("winding_rul_days")
            if any(v is not None for v in [ins, oil, wnd]):
                rul_rec = RULPrediction(
                    transformer_id      = tid,
                    timestamp           = ts,
                    insulation_rul_days = ins,
                    oil_rul_days        = oil,
                    winding_rul_days    = wnd,
                    overall_health_score= result.get("overall_health_score"),
                )
                session.add(rul_rec)

                # Auto work order for critical RUL
                rul_alert = result.get("rul_alert")
                if rul_alert == "CRITICAL":
                    min_rul = min(v for v in [ins, oil, wnd] if v is not None)
                    wo_title = f"[RUL-CRITICAL] Component replacement needed — {tid} ({min_rul:.0f} days)"
                    existing = (session.query(WorkOrder)
                                .filter(WorkOrder.transformer_id == tid,
                                        WorkOrder.title == wo_title,
                                        WorkOrder.status != "CLOSED")
                                .first())
                    if not existing:
                        session.add(WorkOrder(
                            transformer_id = tid,
                            title          = wo_title,
                            description    = (
                                f"Insulation RUL: {ins:.0f} days | "
                                f"Oil RUL: {oil:.0f} days | "
                                f"Winding RUL: {wnd:.0f} days"
                            ),
                            priority       = "CRITICAL",
                            status         = "OPEN",
                            created_at     = datetime.now(),
                        ))

        session.commit()

    except Exception as e:
        log.error(f"[PIPELINE] Error processing packet for {tid}: {e}")
        session.rollback()
    finally:
        session.close()

    # ── Broadcast to WebSocket clients (fire-and-forget) ─────────────────────
    broadcast_data = {
        "transformer_id":  tid,
        "timestamp":       pkt.get("timestamp"),
        "loading_pct":     pkt.get("loading_pct"),
        "oil_temp":        pkt.get("oil_temp"),
        "power_factor":    pkt.get("power_factor"),
        "active_power":    pkt.get("active_power"),
        "fault_class":     result.get("fault_class"),
        "fault_name":      result.get("fault_name"),
        "fault_severity":  result.get("fault_severity"),
        "anomaly_score":   result.get("anomaly_score"),
        "status":          {"NORMAL": "NORMAL", "LOW": "WARNING", "MEDIUM": "WARNING",
                            "HIGH": "FAULT", "CRITICAL": "CRITICAL"}.get(
                                result.get("fault_severity", "NORMAL"), "NORMAL"),
    }
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(broadcast_data), loop)
    except RuntimeError:
        pass


# ─── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("[DTMS] Initialising database…")
    init_db()

    log.info("[DTMS] Loading ML models…")
    ok = load_models()
    if not ok:
        log.warning("[DTMS] Models not found — run setup.py first. Inference disabled.")

    log.info("[DTMS] Starting simulation orchestrator…")
    register_packet_callback(_process_packet)
    orchestrator.start()

    yield  # ── app running ──

    log.info("[DTMS] Shutting down orchestrator…")
    orchestrator.stop()


# ─── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="DTMS — Distribution Transformer Management System",
    description="Real-time AI/ML fault detection and power flow monitoring for utility grid transformers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(fleet.router)
app.include_router(alerts.router)
app.include_router(work_orders.router)
app.include_router(rul_routes.router)


# ─── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws/fleet")
async def websocket_fleet(ws: WebSocket):
    """Live fleet status broadcast — one message per telemetry packet across all transformers."""
    await ws_manager.connect(ws)
    try:
        while True:
            await asyncio.sleep(60)   # keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "simulator_running": orchestrator.running,
        "ws_clients": len(ws_manager.active),
    }
