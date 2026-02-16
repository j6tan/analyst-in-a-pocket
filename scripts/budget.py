import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from style_utils import inject_global_css, show_disclaimer
from data_handler import cloud_input, sync_widget, supabase

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME ---
PRIMARY_GOLD = "#CEB36F"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"

# --- 2. INITIALIZATION ---
if 'budget' not in st.session_state.app_db:
    st.session_state.app_db['budget'] = {}

# --- 3. HEADER ---
st.title("Monthly Lifestyle Budget")
st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid #DEE2E6; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; margin: 0;">
        <b>The Reality Check:</b> Banks calculate your debts, but they don't know how much you spend on sushi, daycare, or gas. 
        Use this tool to define your <b>"Lifestyle Burn Rate"</b> so we can see what's truly affordable.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 4. INPUT COLUMNS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🥑 Living & Family")
    groceries = cloud_input("Groceries & Household ($)", "budget", "groceries", step=50.0)
    dining = cloud_input("Dining Out & Delivery ($)", "budget", "dining", step=50.0)
    childcare = cloud_input("Childcare / Education ($)", "budget", "childcare", step=100.0)
    pets = cloud_input("Pets ($)", "budget", "pets", step=25.0)

with col2:
    st.subheader("🚗 Transport & Utilities")
    # Note: Car LOANS go in the Profile. This is for gas/insurance/maintenance.
    gas_transit = cloud_input("Gas, Transit & Parking ($)", "budget", "gas_transit", step=50.0)
    car_ins_maint = cloud_input("Car Insurance & Maint. ($)", "budget", "car_ins_maint", step=25.0)
    utilities = cloud_input("Phone, Internet & Subscriptions ($)", "budget", "utilities", step=25.0)
    
st.subheader("🎉 Discretionary & Health")
c3, c4 = st.columns(2)
with c3:
    shopping = cloud_input("Shopping & Hobbies ($)", "budget", "shopping", step=50.0)
    entertainment = cloud_input("Entertainment & Travel Fund ($)", "budget", "entertainment", step=50.0)
with c4:
    health = cloud_input("Health, Gym & Personal Care ($)", "budget", "health", step=25.0)
    misc = cloud_input("Miscellaneous Buffer ($)", "budget", "misc", step=50.0)

# --- 5. CALCULATIONS ---
total_lifestyle = (groceries + dining + childcare + pets + gas_transit + 
                   car_ins_maint + utilities + shopping + entertainment + health + misc)

# --- 6. VISUALIZATION ---
st.divider()
st.subheader("📊 Your Monthly Burn Rate")

metric_col, chart_col = st.columns([1, 2])

with metric_col:
    st.markdown(f"""
    <div style="background-color: #E9ECEF; padding: 20px; border-radius: 10px; text-align: center;">
        <p style="margin: 0; color: {SLATE_ACCENT}; font-size: 0.9em;">Total Lifestyle Spend</p>
        <h2 style="margin: 0; color: #2E2B28; font-size: 2.5em;">${total_lifestyle:,.0f}</h2>
        <p style="margin: 5px 0 0 0; color: #6C757D; font-size: 0.8em;">per month</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 This amount will now be subtracted from your surplus in the **Portfolio Expansion Map** to show your True Cash Flow.")

with chart_col:
    # Prepare data for pie chart
    data = {
        "Food & Dining": groceries + dining,
        "Kids & Pets": childcare + pets,
        "Transport": gas_transit + car_ins_maint,
        "Utilities": utilities,
        "Shopping & Fun": shopping + entertainment,
        "Health & Misc": health + misc
    }
    # Filter out zero values
    clean_data = {k: v for k, v in data.items() if v > 0}
    
    if clean_data:
        fig = go.Figure(data=[go.Pie(labels=list(clean_data.keys()), values=list(clean_data.values()), hole=.4)])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Enter expenses to visualize your budget breakdown.")

show_disclaimer()
