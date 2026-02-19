import streamlit as st
import pandas as pd # Correct
import plotly.graph_objects as go
from style_utils import inject_global_css, show_disclaimer
# ADDED: load_user_data, init_session_state
from data_handler import cloud_input, sync_widget, supabase, load_user_data, init_session_state

# --- UNIVERSAL LOADER START ---
init_session_state()
if not st.session_state.app_db.get('profile') and st.session_state.get('username'):
    with st.spinner("🔄 Hydrating Data..."):
        load_user_data(st.session_state.username)
        st.rerun()
# --- UNIVERSAL LOADER END ---

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
st.title("🥑 Monthly Lifestyle Budget")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 25px;">
    <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.4em;">📋 Strategic Brief: {household_name} Budget</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.6; margin: 0;">
        Real estate success isn't just about what the bank approves—it's about what <b>you</b> can actually live with. 
        Define your non-debt spending below to calculate your true household resilience.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. THE PRO TIP ---
st.info(f"""
**💡 Pro Tip for High-Income Earners:** Banks qualify you based on your 'Ability to Pay Debt.' They don't account for private school, travel, or fine dining. 
A high T4 income might get you approved for two properties, but without an accurate budget, 
the second property might force a significant reduction in your quality of life. 
""")

# --- 5. INPUT COLUMNS ---
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

# --- 6. CALCULATIONS ---
total_lifestyle = (groceries + dining + childcare + pets + gas_transit + 
                   car_ins_maint + utilities + shopping + entertainment + health + misc)

st.divider()
st.subheader("📊 Lifestyle Snapshot")

metric_col, chart_col = st.columns([1, 2])

with metric_col:
    st.markdown(f"""
    <div style="background-color: #E9ECEF; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #DEE2E6;">
        <p style="margin: 0; color: {SLATE_ACCENT}; font-size: 0.9em; font-weight: 600;">{household_name.upper()}'S MONTHLY BUDGET</p>
        <h2 style="margin: 0; color: #2E2B28; font-size: 2.8em;">${total_lifestyle:,.0f}</h2>
        <p style="margin: 10px 0 0 0; color: #dc2626; font-size: 0.85em; font-weight: 500; line-height: 1.3;">
            Note: This is lifestyle spending only. <br>
            Does <u>not</u> include Rent/Mortgage, <br>
            Taxes, Insurance, or Hydro.
        </p>
    </div>
    """, unsafe_allow_html=True)

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
            marker=dict(colors=['#CEB36F', '#4A4E5A', '#889696', '#7D8491', '#EAE0D5']),
            textinfo='label+percent'
        )])
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0), 
            height=280, 
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Start entering expenses to see your household breakdown.")

show_disclaimer()
