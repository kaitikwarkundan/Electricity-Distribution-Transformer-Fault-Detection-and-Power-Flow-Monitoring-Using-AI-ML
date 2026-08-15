"""
pages/3_Alerts.py — Centralised fault & alert management.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

API = "http://127.0.0.1:8000"
st_autorefresh(interval=5000, limit=None, key="alerts_refresh")

st.markdown("""
<h2 style='font-size:1.2rem;font-weight:700;color:#dce8f5;margin-bottom:0.2rem;'>🚨 Fault & Alert Management</h2>
<p style='color:#6e8aaa;font-size:0.8rem;margin-bottom:1rem;'>Real-time AI-detected anomalies and system alerts</p>
""", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    f_sev = st.selectbox("Severity", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "NORMAL"])
with col_f2:
    f_ack = st.selectbox("Status", ["Unacknowledged Only", "All Alerts"])
with col_f3:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

# ── Fetch data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_alerts(sev, ack):
    params = {}
    if sev != "ALL": params["severity"] = sev
    if ack == "Unacknowledged Only": params["acknowledged"] = False
    try:
        r = requests.get(f"{API}/api/alerts", params=params, timeout=3)
        return r.json().get("alerts", [])
    except:
        return []

alerts = fetch_alerts(f_sev, f_ack)

if not alerts:
    st.info("No active alerts matching the selected criteria. System is healthy.")
    st.stop()

# ── Alert List ────────────────────────────────────────────────────────────────
for a in alerts:
    sev   = a.get("severity", "NORMAL")
    tid   = a.get("transformer_id", "")
    ts    = a.get("timestamp", "").replace("T", " ")[:19]
    msg   = a.get("message", "")
    ack   = a.get("acknowledged", False)
    aid   = a.get("id")

    badge_map = {"NORMAL":"badge-normal", "LOW":"badge-warning", "MEDIUM":"badge-warning", "HIGH":"badge-fault", "CRITICAL":"badge-critical"}
    row_map   = {"NORMAL":"alert-NORMAL", "LOW":"alert-LOW", "MEDIUM":"alert-MEDIUM", "HIGH":"alert-HIGH", "CRITICAL":"alert-CRITICAL"}
    
    badge_cls = badge_map.get(sev, "badge-normal")
    row_cls   = row_map.get(sev, "alert-NORMAL")

    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"""
        <div class='alert-row {row_cls}'>
          <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
            <div>
              <span class='badge {badge_cls}' style='margin-right:8px;'>{sev}</span>
              <span style='font-weight:600;color:#dce8f5;font-family:monospace;'>{tid}</span>
            </div>
            <div style='font-size:0.7rem;color:#6e8aaa;'>{ts}</div>
          </div>
          <div style='font-size:0.8rem;color:#dce8f5;'>{msg}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if not ack:
            if st.button("Acknowledge", key=f"ack_{aid}", use_container_width=True):
                try:
                    requests.post(f"{API}/api/alerts/{aid}/acknowledge", json={"acknowledged_by": "Operator"}, timeout=3)
                    st.success("Ack'd")
                    st.rerun()
                except:
                    st.error("Error")
        else:
            st.markdown(f"<div style='font-size:0.7rem;color:#00ff88;text-align:center;padding-top:10px;'>✓ Ack'd by {a.get('acknowledged_by')}</div>", unsafe_allow_html=True)
