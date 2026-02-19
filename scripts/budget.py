import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase, load_user_data, init_session_state
import time

# --- 1. UNIVERSAL AUTO-LOADER ---
init_session_state()
if st.session_state.get('username') and not st.session_state.app_db.get('profile'):
    with st.spinner("🔄 restoring your data..."):
        load_user_data(st.session_state.username)
        time.sleep(0.1)
        st.rerun()

# 2. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("scripts/home.py")
st.divider()

# --- 3. PAGE CONTENT ---
prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Client')
household_name = p1_name

if 'budget' not in st.session_state.app_db:
    st.session_state.app_db['budget'] = {}

st.title("🥑 Monthly Lifestyle Budget")
st.markdown(f"Plan for **{household_name}**")

col1, col2 = st.columns(2)

# STRICT INTEGER INPUTS (step=50, step=25)
# This prevents the "Float vs Int" crash that causes blank inputs
with col1:
    st.subheader("🛒 The Essentials")
    groceries = cloud_input("Groceries & Home Supplies ($)", "budget", "groceries", step=50)
    utilities = cloud_input("Phone, Internet & Power ($)", "budget", "utilities", step=25)
    health = cloud_input("Gym, Health & Personal Care ($)", "budget", "health", step=25)
    
    st.write("")
    st.subheader("👨‍👩‍👧 Family & Dependents")
    childcare = cloud_input("Daycare / Education ($)", "budget", "childcare", step=100)
    pets = cloud_input("Pet Food & Vet Costs ($)", "budget", "pets", step=25)

with col2:
    st.subheader("🥂 Quality of Life")
    dining = cloud_input("Dining Out & Weekend Fun ($)", "budget", "dining", step=50)
    shopping = cloud_input("Retail, Hobbies & Gear ($)", "budget", "shopping", step=50)
    entertainment = cloud_input("Travel Fund & Subscriptions ($)", "budget", "entertainment", step=50)
    
    st.write("")
    st.subheader("🚗 Getting Around")
    gas_transit = cloud_input("Gas, Transit & Parking ($)", "budget", "gas_transit", step=50)
    car_ins_maint = cloud_input("Insurance & Maintenance ($)", "budget", "car_ins_maint", step=25)
    misc = cloud_input("The 'Anything Else' Buffer ($)", "budget", "misc", step=50)

# Calculations
total_lifestyle = (groceries + dining + childcare + pets + gas_transit + 
                   car_ins_maint + utilities + shopping + entertainment + health + misc)

st.divider()
st.subheader("📊 Lifestyle Snapshot")

metric_col, chart_col = st.columns([1, 2])
with metric_col:
    st.metric("Total Monthly Spend", f"${total_lifestyle:,.0f}")
    st.caption("Does not include Mortgage/Rent or Taxes")

with chart_col:
    data = {
        "Essentials": groceries + utilities + health,
        "Family": childcare + pets,
        "Fun": dining + shopping + entertainment,
        "Transport": gas_transit + car_ins_maint,
        "Buffer": misc
    }
    clean_data = {k: v for k, v in data.items() if v > 0}
    
    if clean_data:
        fig = go.Figure(data=[go.Pie(labels=list(clean_data.keys()), values=list(clean_data.values()), hole=.4)])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
        st.plotly_chart(fig, use_container_width=True)

show_disclaimer()
