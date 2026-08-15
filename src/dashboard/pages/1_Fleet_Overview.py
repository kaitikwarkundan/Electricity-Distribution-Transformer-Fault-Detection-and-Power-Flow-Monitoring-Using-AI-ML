"""
pages/1_Fleet_Overview.py — City-grid fleet status map + live KPIs.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

API = "http://127.0.0.1:8000"
st_autorefresh(interval=3000, limit=None, key="fleet_refresh")

st.markdown("""
<h2 style='font-size:1.2rem;font-weight:700;color:#dce8f5;margin-bottom:0.2rem;'>🗺️ Fleet Grid Overview</h2>
<p style='color:#6e8aaa;font-size:0.8rem;margin-bottom:1rem;'>Live status of all 12 distribution transformers across 4 city zones</p>
""", unsafe_allow_html=True)

# ── Fetch data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_fleet():
    try:
        r = requests.get(f"{API}/api/fleet", timeout=3)
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=2)
def fetch_summary():
    try:
        r = requests.get(f"{API}/api/reports/summary", timeout=3)
        return r.json()
    except Exception:
        return None

fleet_data = fetch_fleet()
summary    = fetch_summary()

if not fleet_data:
    st.error("⚠️ Cannot connect to DTMS API. Make sure the backend is running: `uvicorn src.api.main:app --port 8000`")
    st.stop()

transformers = fleet_data.get("transformers", [])
summary = summary or {}

# ── Fleet KPIs ────────────────────────────────────────────────────────────────
total    = summary.get("total_transformers", len(transformers))
healthy  = summary.get("healthy", 0)
faulted  = summary.get("faulted", 0)
critical = summary.get("critical", 0)
avg_load = summary.get("avg_loading_pct", 0)
total_pw = summary.get("total_active_power_kw", 0)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Transformers", total)
col2.metric("Healthy",  f"{healthy}",   delta=None)
col3.metric("Faulted",  f"{faulted}",   delta=f"+{faulted}" if faulted else None, delta_color="inverse")
col4.metric("Critical", f"{critical}",  delta=f"+{critical}" if critical else None, delta_color="inverse")
col5.metric("Avg Loading", f"{avg_load:.1f}%")
col6.metric("Total Power", f"{total_pw:.0f} kW")

st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)

# ── Grid map (scatter map using lat/lon) ──────────────────────────────────────
STATUS_COLOR = {
    "NORMAL":   "#00ff88",
    "WARNING":  "#ffb800",
    "FAULT":    "#ff3348",
    "CRITICAL": "#ff0033",
}
SEVERITY_SIZE = {"NORMAL": 14, "WARNING": 16, "FAULT": 18, "CRITICAL": 22}

lats, lons, ids, names, texts, colors, sizes = [], [], [], [], [], [], []
for t in transformers:
    status = t.get("status", "NORMAL")
    lats.append(t.get("lat", 28.65))
    lons.append(t.get("lon", 77.20))
    ids.append(t["id"])
    names.append(t["name"])
    colors.append(STATUS_COLOR.get(status, "#00ff88"))
    sizes.append(SEVERITY_SIZE.get(status, 14))
    texts.append(
        f"<b>{t['id']}</b><br>"
        f"Status: {status}<br>"
        f"Load: {t.get('loading_pct', 0):.1f}%<br>"
        f"Oil: {t.get('oil_temp', 0):.1f}°C<br>"
        f"Fault: {t.get('fault_name', 'Normal')}"
    )

fig_map = go.Figure()
fig_map.add_trace(go.Scattermap(
    lat=lats, lon=lons,
    mode="markers+text",
    marker=dict(size=sizes, color=colors, opacity=0.9),
    text=ids,
    textposition="top center",
    textfont=dict(color="#00d4ff", size=10),
    hovertext=texts,
    hoverinfo="text",
    customdata=ids,
))
fig_map.update_layout(
    map=dict(style="carto-darkmatter", center=dict(lat=28.67, lon=77.20), zoom=10),
    margin=dict(l=0, r=0, t=0, b=0),
    height=400,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_map, use_container_width=True)

# ── Transformer status grid ───────────────────────────────────────────────────
st.markdown("<div class='section-header'>Transformer Fleet Status</div>", unsafe_allow_html=True)

cols_per_row = 3
rows = [transformers[i:i+cols_per_row] for i in range(0, len(transformers), cols_per_row)]

for row in rows:
    cols = st.columns(cols_per_row)
    for col, t in zip(cols, row):
        status   = t.get("status", "NORMAL")
        badge_cls= {"NORMAL":"badge-normal","WARNING":"badge-warning","FAULT":"badge-fault","CRITICAL":"badge-critical"}.get(status,"badge-normal")
        load_pct = t.get("loading_pct", 0) or 0
        oil      = t.get("oil_temp", 0) or 0
        pf       = t.get("power_factor", 0) or 0
        fault_nm = t.get("fault_name", "Normal Operation")
        conf     = t.get("fault_confidence", 1.0) or 1.0

        # Loading bar color
        bar_color = "#00ff88" if load_pct < 80 else ("#ffb800" if load_pct < 100 else "#ff3348")
        bar_w = min(100, load_pct)

        with col:
            st.markdown(f"""
            <div class='dtms-card' style='margin-bottom:0.6rem;'>
              <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                <div>
                  <div class='tr-tile-id'>{t['id']}</div>
                  <div class='tr-tile-name'>{t['zone']} · {t['type']}</div>
                </div>
                <span class='badge {badge_cls}'>{status}</span>
              </div>
              <div style='margin-top:0.6rem;'>
                <div style='display:flex;justify-content:space-between;font-size:0.68rem;color:#6e8aaa;margin-bottom:3px;'>
                  <span>Loading</span><span style='color:{bar_color};'>{load_pct:.1f}%</span>
                </div>
                <div style='background:rgba(255,255,255,0.06);border-radius:3px;height:5px;overflow:hidden;'>
                  <div style='width:{bar_w:.0f}%;height:100%;background:{bar_color};border-radius:3px;'></div>
                </div>
              </div>
              <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.3rem;margin-top:0.6rem;font-size:0.7rem;'>
                <div style='text-align:center;background:rgba(0,0,0,0.3);border-radius:6px;padding:4px;'>
                  <div style='color:#6e8aaa;font-size:0.6rem;'>OIL °C</div>
                  <div style='color:#dce8f5;font-weight:600;'>{oil:.0f}</div>
                </div>
                <div style='text-align:center;background:rgba(0,0,0,0.3);border-radius:6px;padding:4px;'>
                  <div style='color:#6e8aaa;font-size:0.6rem;'>P.F.</div>
                  <div style='color:#dce8f5;font-weight:600;'>{pf:.3f}</div>
                </div>
                <div style='text-align:center;background:rgba(0,0,0,0.3);border-radius:6px;padding:4px;'>
                  <div style='color:#6e8aaa;font-size:0.6rem;'>KVA</div>
                  <div style='color:#dce8f5;font-weight:600;'>{t.get("rated_kva",0)}</div>
                </div>
              </div>
              <div style='margin-top:0.6rem;font-size:0.68rem;color:#6e8aaa;'>
                ⚡ {fault_nm} <span style='color:{"#ff3348" if status!="NORMAL" else "#00ff88"};'>({conf:.0%})</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ── Zone power distribution bar chart ─────────────────────────────────────────
st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>Zone Power Distribution</div>", unsafe_allow_html=True)

zones = {}
for t in transformers:
    z = t.get("zone", "Unknown")
    zones.setdefault(z, 0)
    zones[z] += t.get("active_power", 0) or 0

fig_bar = go.Figure(go.Bar(
    x=list(zones.keys()),
    y=[round(v,1) for v in zones.values()],
    marker_color=["#00d4ff","#00ff88","#ffb800","#ff6b35"],
    marker_line_color="rgba(0,0,0,0.3)",
    text=[f"{v:.0f} kW" for v in zones.values()],
    textposition="outside",
    textfont=dict(color="#dce8f5", size=11),
))
fig_bar.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(6,11,22,0.8)",
    font=dict(color="#dce8f5", family="Inter"),
    xaxis=dict(gridcolor="rgba(0,212,255,0.07)"),
    yaxis=dict(title="Active Power (kW)", gridcolor="rgba(0,212,255,0.07)"),
    margin=dict(l=50, r=20, t=20, b=40),
    height=260,
)
st.plotly_chart(fig_bar, use_container_width=True)
