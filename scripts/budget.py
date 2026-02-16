import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("scripts/home.py")
st.divider()

# --- 1. THEME & IDENTITY ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# Pull Personalization Data
prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Primary Client')
p2_name = prof.get('p2_name', '')
household_name = f"{p1_name} & {p2_name}" if p2_name else p1_name

# --- 2. INITIALIZATION ---
if 'budget' not in st.session_state.app_db:
    st.session_state.app_db['budget'] = {}

# --- 3. PERSONALIZED HEADER ---
st.title("🥑 The Lifestyle Burn Rate")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📋 Strategic Brief: {household_name} Lifestyle</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        Real estate success isn't just about what the bank approves—it's about what <b>{p1_name}</b> can actually live with. 
        Define your non-debt spending below to calculate your true household resilience.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. RELATABLE INPUT COLUMNS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🛒 The Essentials")
    groceries = cloud_input("Groceries & Home Supplies ($)", "budget", "groceries", step=50.0)
    utilities = cloud_input("Phone, Internet & Power ($)", "budget", "utilities", step=25.0)
    health = cloud_input("Gym, Health & Personal Care ($)", "budget", "health", step=25.0)
    
    st.write("")
    st.subheader("👨‍👩‍👧 Family & Dependents")
    childcare = cloud_input("Daycare / Education ($)", "budget", "childcare", step=100.0)
    pets = cloud_input("Pet Food & Vet Costs ($)", "budget", "pets", step=25.0)

with col2:
    st.subheader("🥂 Quality of Life")
    dining = cloud_input("Dining Out & Weekend Fun ($)", "budget", "dining", step=50.0)
    shopping = cloud_input("Retail, Hobbies & Gear ($)", "budget", "shopping", step=50.0)
    entertainment = cloud_input("Travel Fund & Subscriptions ($)", "budget", "entertainment", step=50.0)
    
    st.write("")
    st.subheader("🚗 Getting Around")
    gas_transit = cloud_input("Gas, Transit & Parking ($)", "budget", "gas_transit", step=50.0)
    car_ins_maint = cloud_input("Insurance & Maintenance ($)", "budget", "car_ins_maint", step=25.0)
    misc = cloud_input("The 'Anything Else' Buffer ($)", "budget", "misc", step=50.0)

# --- 5. CALCULATIONS ---
total_lifestyle = (groceries + dining + childcare + pets + gas_transit + 
                   car_ins_maint + utilities + shopping + entertainment + health + misc)

# --- 6. VISUALIZATION & IMPACT ---
st.divider()
st.subheader("📊 Monthly Lifestyle Snapshot")

metric_col, chart_col = st.columns([1, 2])

with metric_col:
    st.markdown(f"""
    <div style="background-color: #E9ECEF; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #DEE2E6;">
        <p style="margin: 0; color: {SLATE_ACCENT}; font-size: 0.9em; font-weight: 600;">{p1_name.upper()}'S BURN RATE</p>
        <h2 style="margin: 0; color: #2E2B28; font-size: 2.8em;">${total_lifestyle:,.0f}</h2>
        <p style="margin: 5px 0 0 0; color: #6C757D; font-size: 0.9em;">leaving the pocket monthly</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info(f"💡 This budget represents your **Lifestyle Threshold**. Your investment strategy will now account for this to ensure you aren't 'House Poor'.")

with chart_col:
    data = {
        "Essentials": groceries + utilities + health,
        "Family/Pets": childcare + pets,
        "Fun & Shopping": dining + shopping + entertainment,
        "Transport": gas_transit + car_ins_maint,
        "Buffer": misc
    }
    clean_data = {k: v for k, v in data.items() if v > 0}
    
    if clean_data:
        fig = go.Figure(data=[go.Pie(
            labels=list(clean_data.keys()), 
            values=list(clean_data.values()), 
            hole=.4,
            marker=dict(colors=['#CEB36F', '#4A4E5A', '#DEE2E6', '#A52A2A', '#1B4D3E'])
        )])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Start entering expenses to see your household breakdown.")

show_disclaimer()
