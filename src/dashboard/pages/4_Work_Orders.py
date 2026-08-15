"""
pages/4_Work_Orders.py — Maintenance & RUL work order tracking.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

API = "http://127.0.0.1:8000"
st_autorefresh(interval=10000, limit=None, key="wo_refresh")

st.markdown("""
<h2 style='font-size:1.2rem;font-weight:700;color:#dce8f5;margin-bottom:0.2rem;'>🔧 Maintenance Work Orders</h2>
<p style='color:#6e8aaa;font-size:0.8rem;margin-bottom:1rem;'>Track and manage AI-generated and manual repair jobs</p>
""", unsafe_allow_html=True)

# ── Filters ───────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    f_stat = st.selectbox("Status", ["OPEN", "IN_PROGRESS", "CLOSED", "ALL"])
with c2:
    f_pri  = st.selectbox("Priority", ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"])
with c3:
    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    if st.button("➕ Create Manual WO", use_container_width=True):
        st.session_state.show_create = not st.session_state.get("show_create", False)

# ── Manual creation form ──────────────────────────────────────────────────────
if st.session_state.get("show_create", False):
    with st.container():
        st.markdown("<div class='dtms-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-header'>Create Work Order</div>", unsafe_allow_html=True)
        with st.form("create_wo_form"):
            tc1, tc2 = st.columns(2)
            wo_tr = tc1.text_input("Transformer ID (e.g. TR-N01)")
            wo_pri = tc2.selectbox("Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            wo_title = st.text_input("Title")
            wo_desc = st.text_area("Description")
            if st.form_submit_button("Submit"):
                try:
                    requests.post(f"{API}/api/work-orders", json={
                        "transformer_id": wo_tr, "title": wo_title,
                        "description": wo_desc, "priority": wo_pri
                    }, timeout=3)
                    st.success("Work order created.")
                    st.session_state.show_create = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# ── Fetch Data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_wos(stat, pri):
    params = {}
    if stat != "ALL": params["status"] = stat
    if pri != "ALL":  params["priority"] = pri
    try:
        r = requests.get(f"{API}/api/work-orders", params=params, timeout=3)
        return r.json().get("work_orders", [])
    except:
        return []

wos = fetch_wos(f_stat, f_pri)

if not wos:
    st.info("No work orders found.")
    st.stop()

# ── WO Table ──────────────────────────────────────────────────────────────────
for wo in wos:
    wid = wo.get("id")
    stat = wo.get("status")
    pri = wo.get("priority")
    ts = wo.get("created_at", "").replace("T", " ")[:16]
    
    pri_color = {"CRITICAL": "#ff0033", "HIGH": "#ff3348", "MEDIUM": "#ffb800", "LOW": "#00ff88"}.get(pri, "#6e8aaa")
    
    with st.expander(f"WO-{wid} | {wo.get('transformer_id')} | {wo.get('title')} ({stat})"):
        st.markdown(f"""
        <div style='font-size:0.8rem; margin-bottom:1rem;'>
          <div><b>Priority:</b> <span style='color:{pri_color};'>{pri}</span></div>
          <div><b>Created:</b> {ts}</div>
          <div style='margin-top:0.5rem;color:#6e8aaa;'>{wo.get('description','No description')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        c_act1, c_act2, c_act3 = st.columns(3)
        with c_act1:
            if stat == "OPEN" and st.button("Start Work", key=f"start_{wid}"):
                requests.patch(f"{API}/api/work-orders/{wid}", json={"status": "IN_PROGRESS"}, timeout=3)
                st.rerun()
        with c_act2:
            if stat in ["OPEN", "IN_PROGRESS"] and st.button("Close Order", key=f"close_{wid}"):
                requests.patch(f"{API}/api/work-orders/{wid}", json={"status": "CLOSED"}, timeout=3)
                st.rerun()
