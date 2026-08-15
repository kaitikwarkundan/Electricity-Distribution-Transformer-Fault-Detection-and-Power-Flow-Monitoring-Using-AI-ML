"""
pages/5_AI_Reports.py — Fleet-wide ML and RUL analytics.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

API = "http://127.0.0.1:8000"
st_autorefresh(interval=60000, limit=None, key="reports_refresh")

st.markdown("""
<h2 style='font-size:1.2rem;font-weight:700;color:#dce8f5;margin-bottom:0.2rem;'>📊 AI Performance & Analytics</h2>
<p style='color:#6e8aaa;font-size:0.8rem;margin-bottom:1rem;'>Fleet-wide Remaining Useful Life (RUL) projections and ML confidence metrics</p>
""", unsafe_allow_html=True)

# ── Fetch data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def fetch_rul_summary():
    try:
        r = requests.get(f"{API}/api/rul/fleet/summary", timeout=3)
        return r.json().get("fleet_rul", [])
    except:
        return []

ruls = fetch_rul_summary()

if not ruls:
    st.info("Insufficient RUL data. The system requires at least 30 telemetry packets per transformer to generate the first prediction.")
    st.stop()

# ── Fleet Health Leaderboard ──────────────────────────────────────────────────
st.markdown("<div class='section-header'>Fleet Health Leaderboard (Ranked by Criticality)</div>", unsafe_allow_html=True)

df = pd.DataFrame(ruls)
df = df.rename(columns={
    "transformer_id": "ID",
    "name": "Location",
    "overall_health_score": "Health Score",
    "min_rul_days": "Shortest RUL (Days)",
    "insulation_rul_days": "Insulation",
    "oil_rul_days": "Oil",
    "winding_rul_days": "Winding"
})

def color_health(val):
    if val < 40: color = '#ff3348'
    elif val < 70: color = '#ffb800'
    else: color = '#00ff88'
    return f'color: {color}; font-weight: bold;'

def color_rul(val):
    if pd.isna(val): return ''
    if val < 30: color = '#ff3348'
    elif val < 90: color = '#ffb800'
    else: color = '#00ff88'
    return f'color: {color}'

styled_df = df.style.map(color_health, subset=['Health Score']) \
                    .map(color_rul, subset=['Shortest RUL (Days)', 'Insulation', 'Oil', 'Winding']) \
                    .format(precision=0)

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# ── RUL Distribution Chart ────────────────────────────────────────────────────
st.markdown("<hr style='border:none;border-top:1px solid rgba(0,212,255,0.12);margin:0.8rem 0;'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>Shortest Component RUL Distribution</div>", unsafe_allow_html=True)

fig = go.Figure(go.Histogram(
    x=df["Shortest RUL (Days)"],
    xbins=dict(start=0, end=5000, size=50),
    marker_color="#00d4ff",
    opacity=0.8
))
fig.add_vline(x=90, line_dash="dash", line_color="#ffb800", annotation_text="Warning (90d)")
fig.add_vline(x=30, line_dash="dash", line_color="#ff3348", annotation_text="Critical (30d)")
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(6,11,22,0.8)",
    font=dict(color="#dce8f5", family="Inter"),
    xaxis=dict(title="Days Remaining", gridcolor="rgba(0,212,255,0.07)"),
    yaxis=dict(title="Number of Transformers", gridcolor="rgba(0,212,255,0.07)"),
    margin=dict(l=40, r=40, t=20, b=40),
    height=300
)
st.plotly_chart(fig, use_container_width=True)
