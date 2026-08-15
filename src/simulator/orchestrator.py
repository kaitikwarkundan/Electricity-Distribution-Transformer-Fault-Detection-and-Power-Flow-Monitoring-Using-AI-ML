"""
src/simulator/orchestrator.py
Runs all 12 transformer simulators in parallel background threads.
Pushes telemetry packets into the shared live_data store and writes to DB.
"""

import sys, os, time, threading, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime
from collections import deque
from typing import Dict, Optional, Callable

import numpy as np

from config import TRANSFORMER_FLEET, SIMULATION_INTERVAL_SEC, TELEMETRY_HISTORY_LIMIT
from src.simulator.telemetry_generator import TransformerTelemetryGenerator

log = logging.getLogger("orchestrator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ─── Shared in-memory state (read by API / dashboard) ─────────────────────────

# Latest packet per transformer_id
latest: Dict[str, dict] = {}

# Rolling ring-buffer of last N packets per transformer_id
history: Dict[str, deque] = {
    cfg["id"]: deque(maxlen=TELEMETRY_HISTORY_LIMIT)
    for cfg in TRANSFORMER_FLEET
}

# Fault override registry: transformer_id → (mode, severity)
fault_overrides: Dict[str, Optional[tuple]] = {
    cfg["id"]: None for cfg in TRANSFORMER_FLEET
}

# Lock for thread-safe writes to shared state
_lock = threading.Lock()

# Optional write-callback (set by API on startup to write to DB + run ML)
_on_packet: Optional[Callable[[dict], None]] = None


def register_packet_callback(fn: Callable[[dict], None]):
    """Register a function called on every new telemetry packet."""
    global _on_packet
    _on_packet = fn


def inject_fault(transformer_id: str, mode: int, severity: float = 1.0):
    """External API: trigger a fault on a specific transformer."""
    with _lock:
        fault_overrides[transformer_id] = (mode, severity)
    log.info(f"[FAULT INJECTED] {transformer_id} mode={mode} severity={severity:.2f}")


def clear_fault(transformer_id: str):
    """External API: clear a fault on a specific transformer."""
    with _lock:
        fault_overrides[transformer_id] = None
    log.info(f"[FAULT CLEARED] {transformer_id}")


def get_latest(transformer_id: str) -> Optional[dict]:
    return latest.get(transformer_id)


def get_history(transformer_id: str, n: int = 60) -> list:
    buf = history.get(transformer_id, deque())
    packets = list(buf)
    return packets[-n:] if n else packets


def get_all_latest() -> list:
    return [v for v in latest.values() if v]


# ─── Per-transformer worker thread ────────────────────────────────────────────

def _worker(cfg: dict, stop_event: threading.Event):
    gen = TransformerTelemetryGenerator(cfg)
    tid = cfg["id"]
    log.info(f"[SIM] Started generator for {tid}")

    while not stop_event.is_set():
        t0 = time.time()
        ts = datetime.now()

        # Apply fault overrides
        with _lock:
            override = fault_overrides.get(tid)
        if override:
            gen.set_fault(override[0], override[1])
        else:
            gen.clear_fault()

        # Generate packet
        packet = gen.generate(ts)

        # Write to shared store
        with _lock:
            latest[tid]         = packet
            history[tid].append(packet)

        # Fire callback (DB write + ML inference happens here)
        if _on_packet:
            try:
                _on_packet(packet)
            except Exception as e:
                log.error(f"[SIM] Packet callback error for {tid}: {e}")

        elapsed = time.time() - t0
        sleep_for = max(0, SIMULATION_INTERVAL_SEC - elapsed)
        stop_event.wait(sleep_for)

    log.info(f"[SIM] Generator stopped for {tid}")


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class SimulatorOrchestrator:
    def __init__(self):
        self._stop_events: Dict[str, threading.Event] = {}
        self._threads: Dict[str, threading.Thread]    = {}
        self.running = False

    def start(self):
        if self.running:
            return
        log.info(f"[ORCHESTRATOR] Starting {len(TRANSFORMER_FLEET)} transformer simulators…")
        for cfg in TRANSFORMER_FLEET:
            ev = threading.Event()
            t  = threading.Thread(
                target=_worker,
                args=(cfg, ev),
                daemon=True,
                name=f"sim-{cfg['id']}",
            )
            self._stop_events[cfg["id"]] = ev
            self._threads[cfg["id"]]     = t
            t.start()
        self.running = True
        log.info("[ORCHESTRATOR] All simulators running.")

    def stop(self):
        log.info("[ORCHESTRATOR] Stopping all simulators…")
        for ev in self._stop_events.values():
            ev.set()
        for t in self._threads.values():
            t.join(timeout=5)
        self.running = False
        log.info("[ORCHESTRATOR] All simulators stopped.")


# ─── Singleton ────────────────────────────────────────────────────────────────
orchestrator = SimulatorOrchestrator()


if __name__ == "__main__":
    """Quick smoke test — prints one packet per transformer."""
    orchestrator.start()
    time.sleep(3)
    for tid, pkt in latest.items():
        print(f"{tid}: load={pkt['loading_pct']:.1f}%  oil={pkt['oil_temp']:.1f}°C  fault={pkt['fault_label']}")
    orchestrator.stop()
