import streamlit as st
import pandas as pd
import plotly.express as px
from style_utils import inject_global_css, show_disclaimer 
from data_handler import cloud_input, sync_widget

# 1. Inject Style
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. INITIALIZATION ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {}
if 'sales_proceeds' not in st.session_state.app_db:
    st.session_state.app_db['sales_proceeds'] = {}

st.title("💰 Seller's Net Sheet")
st.markdown("""
    <div style="background-color: #F8F9FA; padding: 20px; border-radius: 10px; border-left: 5px solid #CEB36F; margin-bottom: 25px;">
        <h4 style="color: #4A4E5A; margin: 0 0 5px 0;">True Net Estimator</h4>
        <p style="color: #6C757D; font-size: 1.05em; margin: 0; line-height: 1.5;">
            The "Sold Price" isn't what lands in your bank account. 
            This tool strips away commissions, taxes, penalties, and fees to reveal your <b>Real Walk-Away Number</b>.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- 2. INPUT SECTION ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("🏠 Property & Price")
    target_price = cloud_input("Target Sale Price ($)", "sales_proceeds", "target_price", step=5000.0)
    
    # Property Type Logic
    prop_types = ["Primary Residence", "Secondary / Investment"]
    curr_type = st.session_state.app_db['sales_proceeds'].get('prop_type', 'Primary Residence')
    if curr_type not in prop_types: curr_type = 'Primary Residence'
    prop_type = st.selectbox("Property Type", prop_types, index=prop_types.index(curr_type), key="sp_prop_type")
    if prop_type != curr_type:
        st.session_state.app_db['sales_proceeds']['prop_type'] = prop_type
        sync_widget("sales_proceeds:prop_type")

    # Flipping Tax Logic
    is_flip = st.checkbox("Owned less than 365 days? (Anti-Flipping Tax)", key="sp_is_flip")
    
    st.subheader("🏦 Mortgage & Penalties")
    mort_bal = cloud_input("Remaining Mortgage Balance ($)", "sales_proceeds", "mort_bal", step=1000.0)
    
    if mort_bal > 0:
        mort_type = st.radio("Mortgage Type", ["Variable", "Fixed"], horizontal=True, key="sp_mort_type")
        mort_rate = cloud_input("Current Interest Rate (%)", "sales_proceeds", "mort_rate", step=0.1)
        if mort_type == "Fixed":
            months_left = st.number_input("Months Remaining in Term", 0, 60, 24, key="sp_months_left")
        else:
            months_left = 0
    else:
        mort_type, mort_rate, months_left = "Variable", 0, 0

with c2:
    st.subheader("🤝 Commission (Standard Split)")
    st.caption("Calculated on the first $100,000 vs. Balance")
    
    comm_tier1_pct = cloud_input("1st Tier % (First $100k)", "sales_proceeds", "comm_tier1_pct", step=0.1)
    comm_rem_pct = cloud_input("Remaining Balance %", "sales_proceeds", "comm_rem_pct", step=0.1)
    
    st.subheader("⚖️ Closing Costs")
    lawyer_fees = cloud_input("Legal / Notary Fees ($)", "sales_proceeds", "lawyer_fees", step=100.0)
    adjustments = cloud_input("Closing Adjustments (Prop Tax/Strata) ($)", "sales_proceeds", "adjustments", step=100.0)
    staging = cloud_input("Staging & Prep Costs ($)", "sales_proceeds", "staging", step=500.0)
    
    # Capital Gains Setup (Hidden for Primary unless Flipping)
    adjusted_cost_base = 0.0
    marginal_tax_rate = 0.0
    if prop_type == "Secondary / Investment" or is_flip:
        st.markdown("**Tax Details**")
        adjusted_cost_base = cloud_input("Original Purchase Price + Renos (ACB) $", "sales_proceeds", "acb", step=5000.0)
        marginal_tax_rate = st.slider("Est. Marginal Tax Rate (%)", 20, 54, 45, key="sp_tax_rate")

# --- 3. CALCULATION ENGINE ---
def calculate_proceeds(sale_price):
    if sale_price == 0: return {}
    
    # 1. Commission (Standard First 100k Split)
    # Tier 1: First 100k
    c1_amt = 100000 * (comm_tier1_pct / 100) if sale_price >= 100000 else sale_price * (comm_tier1_pct / 100)
    
    # Tier 2: The Rest
    c2_amt = max(0, sale_price - 100000) * (comm_rem_pct / 100)
    
    total_comm = c1_amt + c2_amt
    gst_on_comm = total_comm * 0.05
    
    # 2. Mortgage Penalty
    penalty = 0
    if mort_bal > 0:
        # Variable: Usually 3 months interest
        penalty_3mo = (mort_bal * (mort_rate/100) / 12) * 3
        
        if mort_type == "Variable":
            penalty = penalty_3mo
        else:
            # Fixed: Simplified IRD estimation
            ird_est = (mort_bal * 0.015) * (months_left / 12) 
            penalty = max(penalty_3mo, ird_est)

    # 3. Capital Gains / Tax
    cap_gains_tax = 0
    if (prop_type == "Secondary / Investment" or is_flip) and sale_price > adjusted_cost_base:
        net_gain = (sale_price - total_comm - gst_on_comm - lawyer_fees - staging) - adjusted_cost_base
        if net_gain > 0:
            if is_flip:
                # Anti-Flipping: 100% Inclusion
                cap_gains_tax = net_gain * (marginal_tax_rate / 100)
            else:
                # Standard Cap Gains: 50% Inclusion (Simplified)
                inclusion_amt = net_gain * 0.50
                cap_gains_tax = inclusion_amt * (marginal_tax_rate / 100)

    # 4. Total Costs
    total_costs = (total_comm + gst_on_comm + penalty + lawyer_fees + adjustments + staging + cap_gains_tax)
    
    # 5. Net Proceeds
    net_proceeds = sale_price - mort_bal - total_costs
    
    return {
        "price": sale_price,
        "comm": total_comm,
        "gst": gst_on_comm,
        "penalty": penalty,
        "tax": cap_gains_tax,
        "fees": lawyer_fees + adjustments + staging,
        "total_costs": total_costs,
        "net": net_proceeds
    }

# --- 4. RESULTS ---
if target_price > 0:
    st.divider()
    
    # A. SCENARIO MATRIX (Top)
    st.subheader("📊 Scenario Matrix")
    
    scenarios = [
        {"label": "-5% Price", "price": target_price * 0.95},
        {"label": "TARGET PRICE", "price": target_price},
        {"label": "+5% Price", "price": target_price * 1.05},
    ]
    
    matrix_data = []
    target_res = None
    
    # Calculate scenarios
    cols = st.columns(len(scenarios))
    for i, s in enumerate(scenarios):
        res = calculate_proceeds(s['price'])
        if s['label'] == "TARGET PRICE": target_res = res
        
        # Determine Color
        bg_color = "#F8F9FA"
        border_color = "#DEE2E6"
        if s['label'] == "TARGET PRICE":
            bg_color = "#FFF8E1" # Gold tint
            border_color = "#CEB36F"
            
        with cols[i]:
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; border: 1px solid {border_color}; text-align: center;">
                <p style="margin:0; font-size: 0.9em; color: #666;">{s['label']}</p>
                <p style="margin:5px 0; font-size: 1.2em; font-weight: bold;">${s['price']:,.0f}</p>
                <hr style="margin: 10px 0; border: 0; border-top: 1px solid #ddd;">
                <p style="margin:0; font-size: 0.8em; color: #666;">NET TO YOU</p>
                <p style="margin:0; font-size: 1.4em; font-weight: bold; color: #16A34A;">${res['net']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.write("") # Spacer

    # B. THE NET SHEET (Detailed Breakdown)
    st.subheader("📉 Official Net Sheet (Target Price)")
    
    # CSS for the Table
    st.markdown("""
    <style>
        .net-sheet-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #eee; font-size: 1.05em; }
        .net-sheet-row.total { border-top: 2px solid #333; border-bottom: none; font-weight: bold; font-size: 1.3em; margin-top: 10px; padding-top: 20px; }
        .net-sheet-label { color: #4A4E5A; }
        .net-sheet-val { font-weight: 500; }
        .negative { color: #DC2626; }
        .positive { color: #16A34A; }
    </style>
    """, unsafe_allow_html=True)

    # Generate the Breakdown HTML
    rows_html = ""
    
    # 1. Sale Price
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Sale Price</span><span class="net-sheet-val">${target_price:,.2f}</span></div>'
    
    # 2. Mortgage
    if mort_bal > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Mortgage Discharge</span><span class="net-sheet-val negative">-${mort_bal:,.2f}</span></div>'
    
    # 3. Commissions
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Real Estate Commission ({comm_tier1_pct}% / {comm_rem_pct}%)</span><span class="net-sheet-val negative">-${target_res["comm"]:,.2f}</span></div>'
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">GST on Commission (5%)</span><span class="net-sheet-val negative">-${target_res["gst"]:,.2f}</span></div>'
    
    # 4. Penalty
    if target_res['penalty'] > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Mortgage Penalty (Est.)</span><span class="net-sheet-val negative">-${target_res["penalty"]:,.2f}</span></div>'
    
    # 5. Fees
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Legal & Adjustments</span><span class="net-sheet-val negative">-${target_res["fees"]:,.2f}</span></div>'
    
    # 6. Taxes
    if target_res['tax'] > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Capital Gains / Flipping Tax</span><span class="net-sheet-val negative">-${target_res["tax"]:,.2f}</span></div>'

    # 7. Total
    rows_html += f'<div class="net-sheet-row total"><span class="net-sheet-label">ESTIMATED NET PROCEEDS</span><span class="net-sheet-val positive">${target_res["net"]:,.2f}</span></div>'

    # Render Container
    st.markdown(f"""
    <div style="background-color: white; padding: 30px; border-radius: 12px; border: 1px solid #DEE2E6; max-width: 800px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        {rows_html}
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Note: This is an estimate. Penalties and taxes vary based on exact lender terms and CRA assessments.")

else:
    st.info("👈 Enter a target price to generate the analysis.")

show_disclaimer()
