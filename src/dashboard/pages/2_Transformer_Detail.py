"""
pages/2_Transformer_Detail.py — Deep-dive view for a single transformer.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

API = "http://127.0.0.1:8000"
st_autorefresh(interval=3000, limit=None, key="detail_refresh")

from config import TRANSFORMER_FLEET, FAULT_CLASSES, RUL_CRITICAL_DAYS, RUL_WARNING_DAYS

st.markdown("""
<h2 style='font-size:1.2rem;font-weight:700;color:#dce8f5;margin-bottom:0.2rem;'>🔍 Transformer Detail</h2>
<p style='color:#6e8aaa;font-size:0.8rem;margin-bottom:1rem;'>Real-time telemetry, power flow analysis, and component health for a selected transformer</p>
""", unsafe_allow_html=True)

# ── Transformer selector ──────────────────────────────────────────────────────
tr_ids = [t["id"] for t in TRANSFORMER_FLEET]
tr_labels = {t["id"]: f"{t['id']} — {t['name']}" for t in TRANSFORMER_FLEET}
selected = st.selectbox("Select Transformer", tr_ids, format_func=lambda x: tr_labels[x])

# ── Fetch data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_detail(tid):
    try:
        return requests.get(f"{API}/api/transformer/{tid}", timeout=3).json()
    except:
        return None

@st.cache_data(ttl=2)
def fetch_history(tid, n=120):
    try:
        return requests.get(f"{API}/api/transformer/{tid}/history?n={n}", timeout=3).json()
    except:
        return None

@st.cache_data(ttl=10)
def fetch_rul(tid):
    try:
        return requests.get(f"{API}/api/rul/{tid}", timeout=3).json()
    except:
        return None

detail = fetch_detail(selected)
history_data = fetch_history(selected)
rul_data = fetch_rul(selected)

if not detail:
    st.error("⚠️ Cannot connect to API.")
    st.stop()

# ── Header status bar ─────────────────────────────────────────────────────────
status   = detail.get("status", "NORMAL")
fault_nm = detail.get("fault_name", "Normal Operation")
conf     = detail.get("fault_confidence", 1.0) or 1.0
anom     = detail.get("anomaly_score", 0.0) or 0.0
badge_map= {"NORMAL":"badge-normal","WARNING":"badge-warning","FAULT":"badge-fault","CRITICAL":"badge-critical"}
badge_cls= badge_map.get(status, "badge-normal")

st.markdown(f"""
<div class='dtms-card' style='margin-bottom:0.8rem;'>
  <div style='display:flex;justify-content:space-between;align-items:center;'>
    <div>
      <span style='font-size:1rem;font-weight:700;color:#00d4ff;font-family:monospace;'>{selected}</span>
      <span style='font-size:0.8rem;color:#6e8aaa;margin-left:0.6rem;'>{detail.get("name","")}</span>
    </div>
    <div style='display:flex;align-items:center;gap:0.8rem;'>
      <span class='badge {badge_cls}'>{status}</span>
      <span style='font-size:0.75rem;color:#6e8aaa;'>⚡ {fault_nm} ({conf:.0%})</span>
      <span style='font-size:0.75rem;color:#6e8aaa;'>Anomaly: {anom:.2f}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Live KPIs ─────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Loading %",    f"{detail.get('loading_pct',0):.1f}%")
c2.metric("Oil Temp",     f"{detail.get('oil_temp',0):.1f}°C")
c3.metric("Power Factor", f"{detail.get('power_factor',0):.3f}")
c4.metric("Active Power", f"{detail.get('active_power',0):.1f} kW")
c5.metric("React. Power", f"{detail.get('reactive_power',0):.1f} kVAR")
c6.metric("Active Alerts",f"{detail.get('active_alert_count',0)}")

st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)

# ── Telemetry charts ──────────────────────────────────────────────────────────
hist = history_data.get("data", []) if history_data else []

if hist:
    timestamps = [h.get("timestamp","") for h in hist]
    va = [h.get("va",0) for h in hist]
    vb = [h.get("vb",0) for h in hist]
    vc = [h.get("vc",0) for h in hist]
    ia = [h.get("ia",0) for h in hist]
    ib = [h.get("ib",0) for h in hist]
    ic = [h.get("ic",0) for h in hist]
    oil= [h.get("oil_temp",0) for h in hist]
    lp = [h.get("loading_pct",0) for h in hist]

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("<div class='section-header'>3-Phase Voltage (V)</div>", unsafe_allow_html=True)
        fig_v = go.Figure()
        for name, vals, col in [("Phase A", va,"#00d4ff"),("Phase B", vb,"#00ff88"),("Phase C", vc,"#ffb800")]:
            fig_v.add_trace(go.Scatter(x=timestamps, y=vals, name=name, line=dict(color=col, width=1.5)))
        fig_v.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(6,11,22,0.8)", font=dict(color="#dce8f5",family="Inter"),
            height=220, margin=dict(l=40,r=10,t=10,b=30),
            xaxis=dict(showticklabels=False, gridcolor="rgba(0,212,255,0.07)"),
            yaxis=dict(title="V", gridcolor="rgba(0,212,255,0.07)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
        st.plotly_chart(fig_v, use_container_width=True)

    with col_right:
        st.markdown("<div class='section-header'>3-Phase Current (A)</div>", unsafe_allow_html=True)
        fig_i = go.Figure()
        for name, vals, col in [("Phase A", ia,"#00d4ff"),("Phase B", ib,"#00ff88"),("Phase C", ic,"#ffb800")]:
            fig_i.add_trace(go.Scatter(x=timestamps, y=vals, name=name, line=dict(color=col, width=1.5)))
        fig_i.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(6,11,22,0.8)", font=dict(color="#dce8f5",family="Inter"),
            height=220, margin=dict(l=40,r=10,t=10,b=30),
            xaxis=dict(showticklabels=False, gridcolor="rgba(0,212,255,0.07)"),
            yaxis=dict(title="A", gridcolor="rgba(0,212,255,0.07)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
        st.plotly_chart(fig_i, use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown("<div class='section-header'>Oil Temperature (°C)</div>", unsafe_allow_html=True)
        fig_oil = go.Figure()
        fig_oil.add_trace(go.Scatter(x=timestamps, y=oil, fill="tozeroy",
            fillcolor="rgba(255,107,53,0.12)", line=dict(color="#ff6b35", width=2)))
        fig_oil.add_hline(y=90, line_color="#ff3348", line_dash="dot", annotation_text="⚠ 90°C threshold")
        fig_oil.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(6,11,22,0.8)", font=dict(color="#dce8f5",family="Inter"),
            height=200, margin=dict(l=40,r=10,t=10,b=30),
            xaxis=dict(showticklabels=False, gridcolor="rgba(0,212,255,0.07)"),
            yaxis=dict(title="°C", gridcolor="rgba(0,212,255,0.07)"))
        st.plotly_chart(fig_oil, use_container_width=True)

    with col_r2:
        st.markdown("<div class='section-header'>Transformer Loading (%)</div>", unsafe_allow_html=True)
        colors_lp = ["#ff3348" if v>100 else "#ffb800" if v>80 else "#00ff88" for v in lp]
        fig_lp = go.Figure()
        fig_lp.add_trace(go.Scatter(x=timestamps, y=lp, fill="tozeroy",
            fillcolor="rgba(0,212,255,0.08)", line=dict(color="#00d4ff", width=2)))
        fig_lp.add_hline(y=100, line_color="#ff3348", line_dash="dot", annotation_text="⚠ Rated capacity")
        fig_lp.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(6,11,22,0.8)", font=dict(color="#dce8f5",family="Inter"),
            height=200, margin=dict(l=40,r=10,t=10,b=30),
            xaxis=dict(showticklabels=False, gridcolor="rgba(0,212,255,0.07)"),
            yaxis=dict(title="%", gridcolor="rgba(0,212,255,0.07)"))
        st.plotly_chart(fig_lp, use_container_width=True)

# ── RUL Panel ─────────────────────────────────────────────────────────────────
st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>🔮 Remaining Useful Life (RUL) Predictions</div>", unsafe_allow_html=True)

rul = rul_data.get("rul") if rul_data else None
if rul:
    ins = rul.get("insulation_rul_days") or 0
    oil_r = rul.get("oil_rul_days") or 0
    wnd = rul.get("winding_rul_days") or 0
    health = rul.get("overall_health_score") or 0

    MAX_INS, MAX_OIL, MAX_WND = 9125, 1825, 10950

    def _rul_bar(label, val, max_val, icon):
        pct = min(100, val / max_val * 100)
        color = "#ff3348" if val < RUL_CRITICAL_DAYS else "#ffb800" if val < RUL_WARNING_DAYS else "#00ff88"
        alert = "🔴 REPLACE NOW" if val < RUL_CRITICAL_DAYS else "🟡 SCHEDULE MAINTENANCE" if val < RUL_WARNING_DAYS else "🟢 HEALTHY"
        return f"""
        <div class='rul-bar-wrap'>
          <div class='rul-bar-label'>
            <span>{icon} {label}</span>
            <span style='color:{color};font-weight:600;'>{val:.0f} days remaining &nbsp;·&nbsp; {alert}</span>
          </div>
          <div class='rul-bar-track'>
            <div class='rul-bar-fill' style='width:{pct:.0f}%;background:{color};'></div>
          </div>
        </div>
        """

    col_rul, col_health = st.columns([3, 1])
    with col_rul:
        st.markdown(f"""
        <div class='dtms-card'>
          {_rul_bar("Insulation Life", ins, MAX_INS, "🛡️")}
          {_rul_bar("Oil Life", oil_r, MAX_OIL, "🛢️")}
          {_rul_bar("Winding Life", wnd, MAX_WND, "🔌")}
        </div>
        """, unsafe_allow_html=True)

    with col_health:
        health_color = "#ff3348" if health < 40 else "#ffb800" if health < 70 else "#00ff88"
        st.markdown(f"""
        <div class='dtms-card' style='text-align:center;padding:1.5rem;'>
          <div style='font-size:0.7rem;color:#6e8aaa;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;'>Overall Health</div>
          <div style='font-size:2.5rem;font-weight:700;color:{health_color};'>{health:.0f}</div>
          <div style='font-size:0.75rem;color:#6e8aaa;'>/100</div>
          <div style='margin-top:0.8rem;font-size:0.72rem;color:{health_color};'>
            {"⚠️ CRITICAL" if health<40 else "⚠️ DEGRADED" if health<70 else "✓ GOOD"}
          </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("RUL data not yet available. Models may still be loading.")

# ── Fault injection control ───────────────────────────────────────────────────
st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)
with st.expander("🧪 Fault Injection Console (Demo Mode)", expanded=False):
    st.markdown("<div style='font-size:0.75rem;color:#ffb800;margin-bottom:0.8rem;'>⚠️ Inject simulated faults for demonstration purposes.</div>", unsafe_allow_html=True)
    fault_options = {v: k for k, v in FAULT_CLASSES.items()}
    sel_fault = st.selectbox("Fault Type", list(FAULT_CLASSES.values()), key="fault_sel")
    severity  = st.slider("Severity", 0.1, 1.0, 0.8, key="fault_sev")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⚡ Inject Fault", key="inject_btn"):
            try:
                resp = requests.post(f"{API}/api/inject-fault", json={
                    "transformer_id": selected,
                    "fault_mode": fault_options[sel_fault],
                    "severity": severity,
                }, timeout=3)
                st.success(f"Fault injected: {resp.json().get('fault_name')}")
            except Exception as e:
                st.error(f"Error: {e}")
    with col_btn2:
        if st.button("✅ Clear Fault", key="clear_btn"):
            try:
                requests.post(f"{API}/api/inject-fault", json={
                    "transformer_id": selected, "fault_mode": 0
                }, timeout=3)
                st.success("Fault cleared.")
            except:
                st.error("Error clearing fault.")
