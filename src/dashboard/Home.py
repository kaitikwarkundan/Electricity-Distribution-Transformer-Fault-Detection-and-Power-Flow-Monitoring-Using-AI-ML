"""
src/dashboard/Home.py — DTMS SCADA Dashboard Main Entry Point.

Run: streamlit run src/dashboard/Home.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import requests

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



def _live_badge_html():
    """Clickable status badge: green LIVE if backend+simulator answer, red OFFLINE otherwise."""
    ok = False
    try:
        h = requests.get("http://127.0.0.1:8000/health", timeout=1.5).json()
        ok = bool(h.get("simulator_running"))
    except Exception:
        pass
    col, bg, txt = ("#00ff88", "rgba(0,255,136,0.12)", "● LIVE") if ok else ("#ff3348", "rgba(255,51,72,0.12)", "● OFFLINE")
    return (f"<a href='http://127.0.0.1:8000/docs' target='_blank' title='Open live API docs' style='text-decoration:none;'>"
            f"<div style='margin-top:0.8rem; padding:4px 12px; background:{bg}; border-radius:20px; display:inline-block; "
            f"font-size:0.65rem; color:{col} !important; border:1px solid {col}; cursor:pointer;'>{txt}</div></a>")

# ── Sidebar branding ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1.5rem 0 1rem;'>
      <div style='font-size:2.4rem;'>⚡</div>
      <div style='font-size:1rem; font-weight:700; color:#00d4ff; letter-spacing:0.12em;'>DTMS</div>
      <div style='font-size:0.65rem; color:#6e8aaa; letter-spacing:0.1em; text-transform:uppercase; margin-top:2px;'>Distribution Transformer<br>Management System</div>
      __LIVE_BADGE__
    </div>
    <hr style='border:none; border-top:1px solid rgba(0,212,255,0.15); margin:0.5rem 0;'>
    """.replace("__LIVE_BADGE__", _live_badge_html()), unsafe_allow_html=True)

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
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import (
    TRANSFORMER_FLEET, FAULT_CLASSES, FAULT_SEVERITY, ML_FEATURE_COLS,
    RUL_INSULATION_FEATURES, RUL_OIL_FEATURES, RUL_WINDING_FEATURES,
    RUL_CRITICAL_DAYS, RUL_WARNING_DAYS, SIMULATION_INTERVAL_SEC,
)

API = "http://127.0.0.1:8000"
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

FAULT_INFO = {
    0: ("Load within 80%, oil &lt; 75 °C", "Monitor"),
    1: ("I &gt; 120% rated, V sag", "Load shed"),
    2: ("Phase A current spike &gt; 300%", "Isolate immediately"),
    3: ("Oil temp &gt; 90 °C, rising dT/dt", "Cooling inspection"),
    4: ("THD &gt; 8%, VUF &gt; 3%", "Load audit"),
    5: ("H₂ ppm rising, DGA spike", "Emergency shutdown"),
}
BADGE = {"NORMAL": "badge-normal", "LOW": "badge-warning", "MEDIUM": "badge-warning",
         "HIGH": "badge-fault", "CRITICAL": "badge-critical"}
SEV_ICON = {"NORMAL": "🟢", "LOW": "🟡", "MEDIUM": "🟠", "HIGH": "🔴", "CRITICAL": "🚨"}


def api_get(path, timeout=3):
    try:
        return requests.get(f"{API}{path}", timeout=timeout).json()
    except Exception:
        return None


# ── Extra styling: KPI cards, architecture cards, module buttons ──────────────
st.markdown("""
<style>
  [data-testid="stSidebarNav"] { display: none; }          /* hide duplicate default menu */
  .kpi { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
         padding: 0.9rem 1rem; text-align: center; transition: all .2s; }
  .kpi:hover { border-color: var(--accent); box-shadow: 0 0 18px var(--accent-glow); transform: translateY(-2px); }
  .kpi-l { font-size: .65rem; letter-spacing: .12em; text-transform: uppercase; color: var(--text-muted); }
  .kpi-v { font-size: 1.7rem; font-weight: 700; margin-top: .2rem; font-family: 'JetBrains Mono', monospace; }
  .kpi-s { font-size: .65rem; color: var(--text-muted); margin-top: .1rem; }
  .arch { text-align: center; padding: 1.1rem .8rem; background: rgba(0,212,255,0.05); border-radius: 12px;
          border: 1px solid rgba(0,212,255,0.15); margin-bottom: .5rem; transition: all .2s; }
  .arch:hover { border-color: var(--accent); box-shadow: 0 0 20px var(--accent-glow); transform: translateY(-2px); }
  .arch.on { border-color: var(--accent); background: rgba(0,212,255,0.12); box-shadow: 0 0 20px var(--accent-glow); }
  .arch .ic { font-size: 2rem; } .arch .t { font-size: .85rem; font-weight: 600; color: var(--accent); margin-top: .4rem; }
  .arch .d { font-size: .7rem; color: var(--text-muted); margin-top: .3rem; min-height: 2.2rem; }
  /* module buttons (page links in the main area) */
  [data-testid="stMain"] a[data-testid="stPageLink-NavLink"] {
    background: linear-gradient(135deg, rgba(0,212,255,0.14), rgba(0,212,255,0.03));
    border: 1px solid rgba(0,212,255,0.35); border-radius: 12px; padding: .85rem .6rem;
    justify-content: center; transition: all .2s; }
  [data-testid="stMain"] a[data-testid="stPageLink-NavLink"]:hover {
    border-color: var(--accent); box-shadow: 0 0 18px var(--accent-glow); transform: translateY(-2px); }
  [data-testid="stMain"] a[data-testid="stPageLink-NavLink"] p { font-weight: 600; color: var(--accent); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style='margin-bottom:1rem;'>
  <h1 style='font-size:1.6rem; font-weight:700; color:#dce8f5; margin:0;'>
    ⚡ Distribution Transformer Management System
  </h1>
  <p style='color:#6e8aaa; font-size:0.85rem; margin-top:0.3rem;'>
    AI/ML-Powered Fault Detection &amp; Power Flow Monitoring — Utility Grid Operations Centre
  </p>
</div>
""", unsafe_allow_html=True)


# ── 1. Live KPI cards (refresh by themselves) ─────────────────────────────────
def kpi(label, value, color="#00d4ff", sub=""):
    return (f"<div class='kpi'><div class='kpi-l'>{label}</div>"
            f"<div class='kpi-v' style='color:{color}'>{value}</div><div class='kpi-s'>{sub}</div></div>")


@st.fragment(run_every=3)
def live_kpis():
    summ = api_get("/api/reports/summary")
    if not summ or "error" in summ:
        st.warning("Backend not reachable or no data yet. Start it with: "
                   "`python -m uvicorn src.api.main:app --port 8000`")
        return
    f_col = "#ff3348" if summ["faulted"] else "#00ff88"
    c_col = "#ff0033" if summ["critical"] else "#00ff88"
    cards = [
        kpi("Transformers", summ["total_transformers"], "#00d4ff", "monitored"),
        kpi("Healthy", summ["healthy"], "#00ff88", "operating normally"),
        kpi("Faulted", summ["faulted"], f_col, "need attention" if summ["faulted"] else "all clear"),
        kpi("Critical", summ["critical"], c_col, "act now" if summ["critical"] else "none"),
        kpi("Total power", f"{summ['total_active_power_kw']:,.0f} kW", "#00d4ff", "active power"),
        kpi("Avg loading", f"{summ['avg_loading_pct']}%", "#ffb800" if summ["avg_loading_pct"] > 85 else "#00d4ff", "of rated capacity"),
    ]
    for col, html in zip(st.columns(6), cards):
        col.markdown(html, unsafe_allow_html=True)

st.markdown("<div class='section-header'>Live Grid Status</div>", unsafe_allow_html=True)
live_kpis()


# ── 2. Module buttons ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header' style='margin-top:1.2rem;'>Open a Module</div>", unsafe_allow_html=True)
nav = [
    ("pages/1_Fleet_Overview.py", "🗺️ Fleet Overview", "Map, status of all 12 transformers, power per zone"),
    ("pages/2_Transformer_Detail.py", "🔍 Transformer Detail", "Live V / I / oil temp / loading, RUL, fault injection"),
    ("pages/3_Alerts.py", "🚨 Fault Alerts", "AI-raised alerts, filter and acknowledge"),
    ("pages/4_Work_Orders.py", "🔧 Work Orders", "Auto-created maintenance jobs, start and close"),
    ("pages/5_AI_Reports.py", "📊 AI Performance", "Health leaderboard and RUL analytics"),
]
for col, (page, label, desc) in zip(st.columns(5), nav):
    with col:
        st.page_link(page, label=label, width="stretch")
        st.caption(desc)


# ── 3. System architecture: click a card to explore ───────────────────────────
st.markdown("<div class='section-header' style='margin-top:1.2rem;'>System Architecture — click a card to explore</div>", unsafe_allow_html=True)

ARCH = [
    ("sim", "🏭", "Simulation Layer", "12 virtual 11kV/415V transformers<br>across 4 city grid zones"),
    ("ml", "🤖", "AI/ML Engine", "3-tier: Isolation Forest +<br>XGBoost + RUL Regressor"),
    ("dash", "📊", "Control Dashboard", "Real-time SCADA UI<br>with live anomaly alerts"),
    ("flow", "🔀", "Data Flow", "Simulator → ML → API<br>→ Database → Dashboard"),
]
if "arch_view" not in st.session_state:
    st.session_state.arch_view = "ml"

for col, (key, icon, title, desc) in zip(st.columns(4), ARCH):
    with col:
        on = st.session_state.arch_view == key
        st.markdown(f"<div class='arch{' on' if on else ''}'><div class='ic'>{icon}</div>"
                    f"<div class='t'>{title}</div><div class='d'>{desc}</div></div>", unsafe_allow_html=True)
        if st.button("● Viewing" if on else "Explore →", key=f"arch_{key}", width="stretch"):
            st.session_state.arch_view = key
            st.rerun()


@st.cache_data
def load_classifier_metrics():
    from sklearn.metrics import classification_report, confusion_matrix
    d = np.load(os.path.join(ROOT, "data", "classifier_test_results.npz"), allow_pickle=True)
    y, p = d["y_test"], d["y_pred"]
    return classification_report(y, p, output_dict=True, zero_division=0), confusion_matrix(y, p)


@st.cache_data
def load_feature_importance():
    import joblib
    m = joblib.load(os.path.join(ROOT, "models", "xgb_classifier.joblib"))
    imp = getattr(m, "feature_importances_", None)
    if imp is None or len(imp) != len(ML_FEATURE_COLS):
        return None
    return pd.DataFrame({"Feature": ML_FEATURE_COLS, "Importance": imp}).sort_values("Importance")


def _style(fig, h=320):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font_color="#dce8f5")
    return fig


def view_sim():
    st.write(f"**{len(TRANSFORMER_FLEET)} virtual 11 kV / 415 V transformers** across 4 city grid zones. "
             f"Each streams a new telemetry packet every **{SIMULATION_INTERVAL_SEC:g} s**: 3-phase voltage and "
             "current, oil temperature, power factor, active/reactive power, loading %, THD, dissolved gas "
             "(H₂ ppm) and rate-of-change features.")
    fleet_df = pd.DataFrame(TRANSFORMER_FLEET)
    zone = st.selectbox("Filter by zone", ["All"] + sorted(fleet_df["zone"].unique()), key="sim_zone")
    view = fleet_df if zone == "All" else fleet_df[fleet_df["zone"] == zone]
    a, b = st.columns([3, 2])
    with a:
        st.dataframe(view[["id", "name", "zone", "type", "rated_kva", "install_year"]]
                     .rename(columns={"id": "ID", "name": "Name", "zone": "Zone", "type": "Type",
                                      "rated_kva": "Rated kVA", "install_year": "Installed"}),
                     width="stretch", hide_index=True)
    with b:
        st.map(view.rename(columns={"lon": "longitude", "lat": "latitude"})[["latitude", "longitude"]],
               width="stretch")


def view_ml():
    st.write("A **3-tier pipeline** runs on every incoming packet:")
    sub1, sub2, sub3 = st.tabs(["Tier 1 · Anomaly", "Tier 2 · Fault classifier", "Tier 3 · RUL"])
    with sub1:
        st.write("**Isolation Forest** (unsupervised). It needs no fault labels: it learns what normal looks "
                 "like and scores every packet, so it can flag unknown abnormal behaviour.")
        st.write("**Input features:**")
        st.code(", ".join(ML_FEATURE_COLS), language=None)
    with sub2:
        st.write("**XGBoost classifier** (supervised). It names the fault from 6 classes.")
        try:
            rep, cm = load_classifier_metrics()
            m = st.columns(4)
            m[0].metric("Accuracy", f"{rep['accuracy']*100:.2f} %")
            m[1].metric("Macro F1", f"{rep['macro avg']['f1-score']:.4f}")
            m[2].metric("Test samples", f"{int(rep['macro avg']['support']):,}")
            m[3].metric("Classes", len(FAULT_CLASSES))
            left, right = st.columns(2)
            with left:
                fig = go.Figure(go.Heatmap(z=cm, x=[str(i) for i in range(6)], y=[str(i) for i in range(6)],
                                           text=cm, texttemplate="%{text}", colorscale="Blues", showscale=False))
                fig.update_layout(title="Confusion matrix (rows = true, cols = predicted)", yaxis=dict(autorange="reversed"))
                st.plotly_chart(_style(fig, 340), width="stretch")
            with right:
                fi = load_feature_importance()
                if fi is not None:
                    fig2 = go.Figure(go.Bar(x=fi["Importance"], y=fi["Feature"], orientation="h", marker_color="#00d4ff"))
                    fig2.update_layout(title="Feature importance")
                    st.plotly_chart(_style(fig2, 340), width="stretch")
                else:
                    st.info("Feature importance not available for this model file.")
            st.caption("Note: results come from synthetic data where fault classes are clearly separable. "
                       "They show the pipeline works, not real-world accuracy.")
        except Exception as e:
            st.info(f"Run `python setup.py` to generate test results. ({e})")
    with sub3:
        st.write("**Three gradient-boosted regressors** predict remaining useful life in days per component, "
                 "combined into an overall health score.")
        comp = st.selectbox("Component", ["Insulation", "Oil", "Winding"], key="rul_comp")
        feats = {"Insulation": RUL_INSULATION_FEATURES, "Oil": RUL_OIL_FEATURES, "Winding": RUL_WINDING_FEATURES}[comp]
        st.write(f"**{comp} RUL features:** " + ", ".join(f"`{f}`" for f in feats))
        st.write(f"Work orders are created automatically: **CRITICAL** if RUL < {RUL_CRITICAL_DAYS} days, "
                 f"**HIGH** if RUL < {RUL_WARNING_DAYS} days.")
        ruls = api_get("/api/rul/fleet/summary")
        if ruls and ruls.get("fleet_rul"):
            col = {"Insulation": "insulation_rul_days", "Oil": "oil_rul_days", "Winding": "winding_rul_days"}[comp]
            rdf = pd.DataFrame(ruls["fleet_rul"])
            if col in rdf:
                fig3 = go.Figure(go.Bar(x=rdf["transformer_id"], y=rdf[col], marker_color="#00d4ff"))
                fig3.update_layout(title=f"Live {comp.lower()} RUL per transformer (days)")
                st.plotly_chart(_style(fig3, 300), width="stretch")
        else:
            st.caption("Live RUL chart appears after about 30 packets per transformer.")


def view_dash():
    st.write("The dashboard has **5 pages**, each backed by a FastAPI endpoint:")
    st.dataframe(pd.DataFrame([
        ["Fleet Overview", "/api/fleet", "Map, status cards, power per zone"],
        ["Transformer Detail", "/api/transformer/{id}", "Live graphs, RUL, fault injection"],
        ["Fault Alerts", "/api/alerts", "Severity filter, acknowledge"],
        ["Work Orders", "/api/work-orders", "Create, start, close maintenance jobs"],
        ["AI Performance", "/api/rul/fleet/summary", "Health ranking, RUL distribution"],
    ], columns=["Page", "API endpoint", "What it does"]), width="stretch", hide_index=True)
    st.link_button("Open API documentation (Swagger)", f"{API}/docs")


def view_flow():
    st.graphviz_chart("""
    digraph G {
      rankdir=LR; bgcolor="transparent";
      node [shape=box, style="rounded,filled", fillcolor="#0f2236", color="#00d4ff", fontcolor="#dce8f5", fontname="Helvetica"];
      edge [color="#6e8aaa"];
      Sim [label="Telemetry Simulator\\n12 transformers"];
      T1  [label="Tier 1\\nIsolation Forest"];
      T2  [label="Tier 2\\nXGBoost classifier"];
      T3  [label="Tier 3\\nRUL regressors"];
      API [label="FastAPI + WebSocket"];
      DB  [label="SQLite DB\\nalerts, work orders, RUL"];
      UI  [label="Streamlit Dashboard"];
      Sim -> T1 -> T2 -> T3 -> API;
      API -> DB; API -> UI; DB -> UI;
    }
    """)


with st.container(border=True):
    {"sim": view_sim, "ml": view_ml, "dash": view_dash, "flow": view_flow}[st.session_state.arch_view]()


# ── 4. Live fault demo ────────────────────────────────────────────────────────
st.markdown("<div class='section-header' style='margin-top:1.2rem;'>🧪 Live Fault Demo</div>", unsafe_allow_html=True)
st.caption("Inject a fault into any transformer and watch the AI detect it in real time.")


@st.fragment(run_every=2)
def demo_console():
    ids = [t["id"] for t in TRANSFORMER_FLEET]
    names = {t["id"]: f"{t['id']} — {t['name']}" for t in TRANSFORMER_FLEET}
    left, right = st.columns([2, 3])
    with left:
        tid = st.selectbox("Transformer", ids, format_func=lambda x: names[x], key="demo_tid")
        fname = st.selectbox("Fault type", [v for k, v in FAULT_CLASSES.items() if k != 0], key="demo_fault")
        sev = st.slider("Severity", 0.1, 1.0, 1.0, key="demo_sev")
        st.caption("Detection time at full severity: overload, short circuit and harmonic ≈ 2 s; "
                   "insulation ≈ 2 s; oil overheating builds gradually (≈ 25 s), as real oil does.")
        mode = {v: k for k, v in FAULT_CLASSES.items()}[fname]
        b1, b2 = st.columns(2)
        if b1.button("⚡ Inject Fault", width="stretch", key="demo_inj"):
            try:
                requests.post(f"{API}/api/inject-fault", timeout=3,
                              json={"transformer_id": tid, "fault_mode": mode, "severity": sev})
                st.toast(f"Injected: {fname} on {tid}")
            except Exception as e:
                st.error(f"Backend not reachable: {e}")
        if b2.button("✅ Clear Fault", width="stretch", key="demo_clr"):
            try:
                requests.post(f"{API}/api/inject-fault", timeout=3, json={"transformer_id": tid, "fault_mode": 0})
                st.toast(f"Cleared {tid}")
            except Exception as e:
                st.error(f"Backend not reachable: {e}")
    with right:
        d = api_get(f"/api/transformer/{tid}")
        if not d or "fault_class" not in d:
            st.info("Waiting for live data…")
            return
        sev_name = FAULT_SEVERITY.get(d["fault_class"], "NORMAL")
        st.markdown(f"#### {SEV_ICON.get(sev_name, '')} {d.get('fault_name')}  ·  {sev_name}")
        m = st.columns(4)
        m[0].metric("Confidence", f"{d.get('fault_confidence', 0)*100:.1f} %")
        m[1].metric("Oil temp", f"{d.get('oil_temp', 0):.1f} °C")
        m[2].metric("Loading", f"{d.get('loading_pct', 0):.1f} %")
        m[3].metric("Anomaly score", f"{d.get('anomaly_score', 0):.2f}")
        st.caption("Open 🚨 Fault Alerts and 🔧 Work Orders to see what the system created automatically.")

demo_console()


# ── 5. Fault classification matrix (styled, with per-class results) ───────────
st.markdown("<div class='section-header' style='margin-top:1.2rem;'>Fault Classification Matrix</div>", unsafe_allow_html=True)
th = "text-align:left; color:#6e8aaa; padding:6px 8px; font-weight:500;"
rows_html = ""
for k, v in FAULT_CLASSES.items():
    sev_n = FAULT_SEVERITY.get(k, "NORMAL")
    rows_html += (
        "<tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>"
        f"<td style='padding:7px 8px; color:#00d4ff; font-family:monospace;'>{k}</td>"
        f"<td style='padding:7px 8px;'>{v}</td>"
        f"<td style='padding:7px 8px;'><span class='badge {BADGE.get(sev_n, 'badge-normal')}'>{sev_n}</span></td>"
        f"<td style='padding:7px 8px; color:#6e8aaa;'>{FAULT_INFO[k][0]}</td>"
        f"<td style='padding:7px 8px; color:#6e8aaa;'>{FAULT_INFO[k][1]}</td></tr>")
st.markdown(f"""
<div class='dtms-card'>
  <table style='width:100%; border-collapse:collapse; font-size:0.78rem;'>
    <tr style='border-bottom:1px solid rgba(0,212,255,0.15);'>
      <th style='{th}'>Class</th><th style='{th}'>Fault Type</th><th style='{th}'>Severity</th>
      <th style='{th}'>Key Indicators</th><th style='{th}'>Action</th></tr>
    {rows_html}
  </table>
</div>""", unsafe_allow_html=True)

pick = st.selectbox("Click a class to see how well the model detects it", list(FAULT_CLASSES.keys()),
                    format_func=lambda k: f"{k} — {FAULT_CLASSES[k]}", key="matrix_pick")
try:
    rep, _ = load_classifier_metrics()
    r = rep[str(pick)]
    c = st.columns(4)
    c[0].metric("Precision", f"{r['precision']:.4f}")
    c[1].metric("Recall", f"{r['recall']:.4f}")
    c[2].metric("F1-score", f"{r['f1-score']:.4f}")
    c[3].metric("Test samples", f"{int(r['support']):,}")
except Exception:
    st.caption("Run `python setup.py` to generate model test results.")


# ── 6. Quick start ────────────────────────────────────────────────────────────
st.markdown("""
<div class='dtms-card'>
  <div class='section-header'>Quick Start</div>
  <div style='font-family:"JetBrains Mono",monospace; font-size:0.78rem; color:#00d4ff; background:rgba(0,0,0,0.3); padding:1rem; border-radius:8px; line-height:1.8;'>
    <span style='color:#6e8aaa;'># Step 1 — Generate data &amp; train models (run once)</span><br>
    <span style='color:#00ff88;'>python</span> setup.py<br><br>
    <span style='color:#6e8aaa;'># Step 2 — Start the simulation + API backend (Terminal 1)</span><br>
    <span style='color:#00ff88;'>python</span> -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000<br><br>
    <span style='color:#6e8aaa;'># Step 3 — Launch this dashboard (Terminal 2)</span><br>
    <span style='color:#00ff88;'>streamlit</span> run src/dashboard/Home.py
  </div>
</div>
""", unsafe_allow_html=True)