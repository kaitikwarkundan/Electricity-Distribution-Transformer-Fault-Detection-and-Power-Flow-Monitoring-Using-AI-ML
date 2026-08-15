"""
src/dashboard/Home.py — DTMS SCADA Dashboard Main Entry Point.

Run: streamlit run src/dashboard/Home.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

st.set_page_config(
    page_title="DTMS — Grid Control Centre",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global SCADA CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  /* ── Root theme ── */
  :root {
    --bg-primary:   #060b16;
    --bg-secondary: #0d1527;
    --bg-card:      rgba(13,21,39,0.85);
    --border:       rgba(0,212,255,0.15);
    --accent:       #00d4ff;
    --accent-glow:  rgba(0,212,255,0.3);
    --text-primary: #dce8f5;
    --text-muted:   #6e8aaa;
    --green:        #00ff88;
    --amber:        #ffb800;
    --red:          #ff3348;
    --critical:     #ff0033;
    --grid:         rgba(0,212,255,0.06);
  }

  /* ── App shell ── */
  .stApp { background: var(--bg-primary) !important; }
  .main .block-container { padding: 1rem 2rem 2rem; max-width: 100%; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070d1c 0%, #0a1628 100%) !important;
    border-right: 1px solid var(--border);
  }
  [data-testid="stSidebar"] * { color: var(--text-primary) !important; }

  /* ── Typography ── */
  html, body, div, p, span, label, .stMarkdown {
    font-family: 'Inter', sans-serif !important;
    color: var(--text-primary);
  }
  code, pre { font-family: 'JetBrains Mono', monospace !important; }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    backdrop-filter: blur(10px);
  }
  [data-testid="stMetricValue"] { color: var(--accent) !important; font-weight: 700 !important; }
  [data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.1em; }

  /* ── Cards ── */
  .dtms-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(0,212,255,0.05);
  }

  /* ── Status badges ── */
  .badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; letter-spacing:0.06em; }
  .badge-normal   { background:rgba(0,255,136,0.15); color:var(--green); border:1px solid rgba(0,255,136,0.4); }
  .badge-warning  { background:rgba(255,184,0,0.15); color:var(--amber); border:1px solid rgba(255,184,0,0.4); }
  .badge-fault    { background:rgba(255,51,72,0.15);  color:var(--red);   border:1px solid rgba(255,51,72,0.4); }
  .badge-critical { background:rgba(255,0,51,0.2);    color:var(--critical); border:1px solid var(--critical); animation:blink 1s step-end infinite; }

  @keyframes blink { 50% { opacity: 0.4; } }

  /* ── Section header ── */
  .section-header {
    font-size: 0.7rem; font-weight: 600; color: var(--accent);
    letter-spacing: 0.15em; text-transform: uppercase;
    border-bottom: 1px solid var(--border); padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
  }

  /* ── Transformer tiles ── */
  .tr-tile {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.6rem;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .tr-tile:hover { border-color: var(--accent); box-shadow: 0 0 20px var(--accent-glow); }
  .tr-tile-id   { font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:var(--accent); font-weight:600; }
  .tr-tile-name { font-size:0.72rem; color:var(--text-muted); margin-top:2px; }

  /* ── Progress bars (RUL) ── */
  .rul-bar-wrap { margin-bottom: 0.8rem; }
  .rul-bar-label { display:flex; justify-content:space-between; font-size:0.72rem; color:var(--text-muted); margin-bottom:4px; }
  .rul-bar-track { background:rgba(255,255,255,0.06); border-radius:4px; height:6px; overflow:hidden; }
  .rul-bar-fill  { height:100%; border-radius:4px; transition:width 0.5s; }

  /* ── Alert rows ── */
  .alert-row { padding:0.6rem 0.8rem; border-radius:8px; margin-bottom:0.4rem; border-left:3px solid; }
  .alert-NORMAL   { background:rgba(0,255,136,0.05); border-color:var(--green); }
  .alert-LOW      { background:rgba(255,230,0,0.05);  border-color:var(--amber); }
  .alert-MEDIUM   { background:rgba(255,184,0,0.08);  border-color:var(--amber); }
  .alert-HIGH     { background:rgba(255,51,72,0.08);   border-color:var(--red); }
  .alert-CRITICAL { background:rgba(255,0,51,0.12);    border-color:var(--critical); }

  /* ── Plotly background fix ── */
  .js-plotly-plot .plotly { background: transparent !important; }

  /* ── Dataframe ── */
  .stDataFrame { border: 1px solid var(--border) !important; border-radius: 10px; }
  .stDataFrame table { color: var(--text-primary) !important; }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(135deg, #0a2a50, #0d3a6e) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    letter-spacing: 0.04em !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #0d3a6e, #0a2a50) !important;
    box-shadow: 0 0 16px var(--accent-glow) !important;
  }

  /* ── Selectbox / inputs ── */
  .stSelectbox > div > div, .stTextInput > div > div {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
  }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg-primary); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar branding ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1.5rem 0 1rem;'>
      <div style='font-size:2.4rem;'>⚡</div>
      <div style='font-size:1rem; font-weight:700; color:#00d4ff; letter-spacing:0.12em;'>DTMS</div>
      <div style='font-size:0.65rem; color:#6e8aaa; letter-spacing:0.1em; text-transform:uppercase; margin-top:2px;'>Distribution Transformer<br>Management System</div>
      <div style='margin-top:0.8rem; padding:4px 10px; background:rgba(0,255,136,0.12); border-radius:20px; display:inline-block; font-size:0.65rem; color:#00ff88; border:1px solid rgba(0,255,136,0.3);'>● LIVE</div>
    </div>
    <hr style='border:none; border-top:1px solid rgba(0,212,255,0.15); margin:0.5rem 0;'>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='font-size:0.65rem; color:#6e8aaa; letter-spacing:0.1em; text-transform:uppercase; padding:0.5rem 0 0.3rem;'>Navigation</div>
    """, unsafe_allow_html=True)

    st.page_link("Home.py",                       label="🏠  Home",                   )
    st.page_link("pages/1_Fleet_Overview.py",      label="🗺️  Fleet Overview",         )
    st.page_link("pages/2_Transformer_Detail.py",  label="🔍  Transformer Detail",     )
    st.page_link("pages/3_Alerts.py",              label="🚨  Fault Alerts",           )
    st.page_link("pages/4_Work_Orders.py",         label="🔧  Work Orders",            )
    st.page_link("pages/5_AI_Reports.py",          label="📊  AI Performance",         )

    st.markdown("<hr style='border:none; border-top:1px solid rgba(0,212,255,0.15);'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.62rem; color:#6e8aaa; text-align:center;'>Utility-Grade AI/ML Monitoring<br>v1.0 — © 2026 DTMS</div>", unsafe_allow_html=True)


# ── Home page content ─────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:1.5rem;'>
  <h1 style='font-size:1.6rem; font-weight:700; color:#dce8f5; margin:0;'>
    ⚡ Distribution Transformer Management System
  </h1>
  <p style='color:#6e8aaa; font-size:0.85rem; margin-top:0.3rem;'>
    AI/ML-Powered Fault Detection &amp; Power Flow Monitoring — Utility Grid Operations Centre
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='dtms-card'>
  <div class='section-header'>System Architecture</div>
  <div style='display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-top:0.8rem;'>
    <div style='text-align:center; padding:1rem; background:rgba(0,212,255,0.05); border-radius:10px; border:1px solid rgba(0,212,255,0.15);'>
      <div style='font-size:1.8rem;'>🏭</div>
      <div style='font-size:0.8rem; font-weight:600; color:#00d4ff; margin-top:0.4rem;'>Simulation Layer</div>
      <div style='font-size:0.7rem; color:#6e8aaa; margin-top:0.3rem;'>12 virtual 11kV/415V transformers<br>across 4 city grid zones</div>
    </div>
    <div style='text-align:center; padding:1rem; background:rgba(0,212,255,0.05); border-radius:10px; border:1px solid rgba(0,212,255,0.15);'>
      <div style='font-size:1.8rem;'>🤖</div>
      <div style='font-size:0.8rem; font-weight:600; color:#00d4ff; margin-top:0.4rem;'>AI/ML Engine</div>
      <div style='font-size:0.7rem; color:#6e8aaa; margin-top:0.3rem;'>3-tier: Isolation Forest +<br>XGBoost + RUL Regressor</div>
    </div>
    <div style='text-align:center; padding:1rem; background:rgba(0,212,255,0.05); border-radius:10px; border:1px solid rgba(0,212,255,0.15);'>
      <div style='font-size:1.8rem;'>📊</div>
      <div style='font-size:0.8rem; font-weight:600; color:#00d4ff; margin-top:0.4rem;'>Control Dashboard</div>
      <div style='font-size:0.7rem; color:#6e8aaa; margin-top:0.3rem;'>Real-time SCADA UI<br>with live anomaly alerts</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='dtms-card'>
  <div class='section-header'>Quick Start</div>
  <div style='font-family:"JetBrains Mono",monospace; font-size:0.78rem; color:#00d4ff; background:rgba(0,0,0,0.3); padding:1rem; border-radius:8px; line-height:1.8;'>
    <span style='color:#6e8aaa;'># Step 1 — Generate data &amp; train models (run once)</span><br>
    <span style='color:#00ff88;'>python</span> setup.py<br><br>
    <span style='color:#6e8aaa;'># Step 2 — Start the simulation + API backend (Terminal 1)</span><br>
    <span style='color:#00ff88;'>uvicorn</span> src.api.main:app --host 127.0.0.1 --port 8000<br><br>
    <span style='color:#6e8aaa;'># Step 3 — Launch this dashboard (Terminal 2)</span><br>
    <span style='color:#00ff88;'>streamlit</span> run src/dashboard/Home.py
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class='dtms-card'>
  <div class='section-header'>Fault Classification Matrix</div>
  <table style='width:100%; border-collapse:collapse; font-size:0.78rem;'>
    <tr style='border-bottom:1px solid rgba(0,212,255,0.15);'>
      <th style='text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;'>Class</th>
      <th style='text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;'>Fault Type</th>
      <th style='text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;'>Severity</th>
      <th style='text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;'>Key Indicators</th>
      <th style='text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;'>Action</th>
    </tr>
    <tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>0</td>
      <td style='padding:7px 8px;'>Normal Operation</td>
      <td style='padding:7px 8px;'><span class='badge badge-normal'>NORMAL</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Load within 80%, Oil &lt;75°C</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Monitor</td>
    </tr>
    <tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>1</td>
      <td style='padding:7px 8px;'>Sustained Overload</td>
      <td style='padding:7px 8px;'><span class='badge badge-warning'>MEDIUM</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>I &gt; 120% rated, V sag</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Load shed</td>
    </tr>
    <tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>2</td>
      <td style='padding:7px 8px;'>SLG Short Circuit</td>
      <td style='padding:7px 8px;'><span class='badge badge-fault'>HIGH</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Phase A current spike &gt;300%</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Isolate immediately</td>
    </tr>
    <tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>3</td>
      <td style='padding:7px 8px;'>Oil Overheating</td>
      <td style='padding:7px 8px;'><span class='badge badge-fault'>HIGH</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Oil Temp &gt;90°C, rising dT/dt</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Cooling inspection</td>
    </tr>
    <tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>4</td>
      <td style='padding:7px 8px;'>Harmonic / Unbalance</td>
      <td style='padding:7px 8px;'><span class='badge badge-warning'>LOW</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>THD &gt;8%, VUF &gt;3%</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Load audit</td>
    </tr>
    <tr>
      <td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>5</td>
      <td style='padding:7px 8px;'>Insulation Breakdown</td>
      <td style='padding:7px 8px;'><span class='badge badge-critical'>CRITICAL</span></td>
      <td style='padding:7px 8px; color:#6e8aaa;'>H₂ ppm rising, DGA spike</td>
      <td style='padding:7px 8px; color:#6e8aaa;'>Emergency shutdown</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)
