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

st.title("💰 Sales Proceeds Calculator")
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
        mort_type, mort_rate, months_left = "Variable", 0, 0

with c2:
    st.subheader("🤝 Commission Structure")
    comm_tier1_pct = cloud_input("1st Tier % (e.g. 7%)", "sales_proceeds", "comm_tier1_pct", step=0.1)
    comm_tier1_amt = cloud_input("1st Tier Cutoff (e.g. $100k)", "sales_proceeds", "comm_tier1_amt", step=10000.0)
    comm_rem_pct = cloud_input("Remaining Balance % (e.g. 2.5%)", "sales_proceeds", "comm_rem_pct", step=0.1)
    
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
    
    # 1. Commission
    c1_amt = min(sale_price, comm_tier1_amt) * (comm_tier1_pct / 100)
    c2_amt = max(0, sale_price - comm_tier1_amt) * (comm_rem_pct / 100)
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
            # Fixed: Greater of 3mo interest or IRD (Simplified IRD estimation)
            # IRD Estimate: Balance * (Current Rate - Posted Rate) * Years Remaining
            # For estimation, we'll assume a 'discount' gap of ~1.5% if not provided, or just use 3mo as floor
            # To be safe for a "Ballpark", we often calculate both and show a range, but here we pick a safe estimate.
            ird_est = (mort_bal * 0.015) * (months_left / 12) # Assuming 1.5% rate differential
            penalty = max(penalty_3mo, ird_est)

    # 3. Capital Gains / Tax
    cap_gains_tax = 0
    if (prop_type == "Secondary / Investment" or is_flip) and sale_price > adjusted_cost_base:
        net_gain = (sale_price - total_comm - gst_on_comm - lawyer_fees - staging) - adjusted_cost_base
        if net_gain > 0:
            if is_flip:
                # Anti-Flipping: 100% Inclusion as Business Income
                cap_gains_tax = net_gain * (marginal_tax_rate / 100)
            else:
                # Standard Cap Gains: 50% Inclusion (Simplified)
                # Note: New 2024 rules (66% over 250k) are complex, staying with 50% for ballpark or adding logic later
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
    
    # A. SCENARIO MATRIX
    st.header("📊 The Scenario Matrix")
    
    scenarios = [
        {"label": "-10% Price", "price": target_price * 0.90},
        {"label": "-5% Price", "price": target_price * 0.95},
        {"label": "TARGET PRICE", "price": target_price},
        {"label": "+5% Price", "price": target_price * 1.05},
        {"label": "+10% Price", "price": target_price * 1.10},
    ]
    
    matrix_data = []
    target_res = None
    
    for s in scenarios:
        res = calculate_proceeds(s['price'])
        if s['label'] == "TARGET PRICE": target_res = res
        
        matrix_data.append({
            "Scenario": s['label'],
            "Sale Price": f"${s['price']:,.0f}",
            "Commissions (+GST)": f"${res['comm'] + res['gst']:,.0f}",
            "Est. Penalty": f"${res['penalty']:,.0f}",
            "Est. Taxes": f"${res['tax']:,.0f}",
            "Net Proceeds": f"${res['net']:,.0f}"
        })
    
    # Display Matrix
    df_matrix = pd.DataFrame(matrix_data)
    st.table(df_matrix.set_index("Scenario"))
    
    # B. DETAILED BREAKDOWN (TARGET)
    st.divider()
    col_breakdown, col_chart = st.columns([1, 1])
    
    with col_breakdown:
        st.subheader("📉 The Breakdown (Target Price)")
        
        st.write(f"**Sale Price:** ${target_price:,.0f}")
        st.write(f"**Mortgage Payoff:** -${mort_bal:,.0f}")
        
        data_rows = [
            ("Real Estate Commission", target_res['comm']),
            ("GST on Commission", target_res['gst']),
            ("Mortgage Penalty (Est.)", target_res['penalty']),
            ("Legal & Closing Costs", target_res['fees']),
        ]
        
        if target_res['tax'] > 0:
            label = "Anti-Flipping Tax" if is_flip else "Capital Gains Tax (Est.)"
            data_rows.append((label, target_res['tax']))
            
        for label, val in data_rows:
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #eee;">
                <span>{label}</span>
                <span style="color: #DC2626;">-${val:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; padding: 15px 0; margin-top: 10px; border-top: 2px solid #4A4E5A; font-weight: bold; font-size: 1.2em;">
            <span>NET TO BANK</span>
            <span style="color: #16A34A;">${target_res['net']:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        # Waterfall Chart Logic
        fig = px.bar(
            x=["Sale Price", "Mortgage", "Commissions", "Taxes/Fees", "Net Proceeds"],
            y=[target_price, -mort_bal, -(target_res['comm']+target_res['gst']), -(target_res['tax']+target_res['fees']+target_res['penalty']), target_res['net']],
            text_auto='$,.2s',
            title="Where the Money Goes",
            color=["Sale Price", "Expense", "Expense", "Expense", "Net"],
            color_discrete_map={"Sale Price": "#4A4E5A", "Expense": "#DC2626", "Net": "#16A34A"}
        )
        fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Enter a target price to generate the analysis.")

show_disclaimer()
