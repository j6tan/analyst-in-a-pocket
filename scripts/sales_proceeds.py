import streamlit as st
import pandas as pd
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
    
    prop_type = st.selectbox(
        "Property Type", 
        prop_types, 
        index=prop_types.index(curr_type), 
        key="sp_prop_type_widget"
    )
    # Sync Selectbox
    if prop_type != curr_type:
        st.session_state.app_db['sales_proceeds']['prop_type'] = prop_type
        sync_widget("sales_proceeds:prop_type")

    # Flipping Tax Logic
    is_flip = st.checkbox("Owned less than 365 days? (Anti-Flipping Tax)", key="sp_is_flip")
    
    st.subheader("🏦 Mortgage & Penalties")
    mort_bal = cloud_input("Remaining Mortgage Balance ($)", "sales_proceeds", "mort_bal", step=1000.0)
    
    if mort_bal > 0:
        m_types = ["Variable", "Fixed"]
        saved_m_type = st.session_state.app_db['sales_proceeds'].get('mort_type', 'Variable')
        if saved_m_type not in m_types: saved_m_type = 'Variable'
        
        mort_type = st.radio(
            "Mortgage Type", 
            m_types, 
            horizontal=True, 
            index=m_types.index(saved_m_type),
            key="sp_mort_type_widget"
        )
        if mort_type != saved_m_type:
            st.session_state.app_db['sales_proceeds']['mort_type'] = mort_type
            sync_widget("sales_proceeds:mort_type")

        mort_rate = cloud_input("Current Interest Rate (%)", "sales_proceeds", "mort_rate", step=0.1)
        
        if mort_type == "Fixed":
            months_left = cloud_input("Months Remaining in Term", "sales_proceeds", "months_left", step=1.0)
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
    
    # Capital Gains Setup
    adjusted_cost_base = 0.0
    marginal_tax_rate = 0.0
    
    if prop_type == "Secondary / Investment" or is_flip:
        st.markdown("---")
        st.markdown("**🏛️ Capital Gains / Tax Details**")
        adjusted_cost_base = cloud_input("Original Purchase Price + Renos (ACB) $", "sales_proceeds", "acb", step=5000.0)
        
        # --- NEW: DYNAMIC TAX CALCULATOR (BC 2025 Est) ---
        def get_marginal_tax_rate(income):
            if income <= 55867: return 20.06
            elif income <= 111733: return 31.00
            elif income <= 173205: return 40.70
            elif income <= 246752: return 45.80
            else: return 53.50

        prof = st.session_state.app_db.get('profile', {})
        p1 = prof.get('p1_name', 'Client 1')
        p2 = prof.get('p2_name', 'Client 2')
        
        # Calculate Real-Time Income Sums
        p1_inc = float(prof.get('p1_t4', 0)) + float(prof.get('p1_bonus', 0)) + float(prof.get('p1_commission', 0))
        p2_inc = float(prof.get('p2_t4', 0)) + float(prof.get('p2_bonus', 0)) + float(prof.get('p2_commission', 0))
        
        t1 = get_marginal_tax_rate(p1_inc)
        t2 = get_marginal_tax_rate(p2_inc)
        
        tax_map = {
            f"{p1} (Inc: ${p1_inc/1000:.0f}k → ~{t1}%)": t1, 
            f"{p2} (Inc: ${p2_inc/1000:.0f}k → ~{t2}%)": t2
        }
        
        st.markdown("#### Whose marginal tax bracket applies?") # Bigger Header
        sel_owner = st.radio("Registered Owner", list(tax_map.keys()), key="sp_tax_owner_radio")
        marginal_tax_rate = tax_map[sel_owner]
        # -------------------------------------------------

# --- 3. CALCULATION ENGINE ---
def calculate_proceeds(sale_price):
    if sale_price == 0: return {}
    
    # 1. Commission
    c1_amt = 100000 * (comm_tier1_pct / 100) if sale_price >= 100000 else sale_price * (comm_tier1_pct / 100)
    c2_amt = max(0, sale_price - 100000) * (comm_rem_pct / 100)
    total_comm = c1_amt + c2_amt
    gst_on_comm = total_comm * 0.05
    
    # 2. Mortgage Penalty
    penalty = 0
    if mort_bal > 0:
        if mort_type == "Fixed" and months_left <= 0:
            penalty = 0
        else:
            penalty_3mo = (mort_bal * (mort_rate/100) / 12) * 3
            if mort_type == "Variable":
                penalty = penalty_3mo
            else:
                ird_est = (mort_bal * 0.015) * (months_left / 12) 
                penalty = max(penalty_3mo, ird_est)

    # 3. Capital Gains / Flipping Tax (Split Logic)
    cap_gains_tax = 0
    flipping_tax = 0
    
    if (prop_type == "Secondary / Investment" or is_flip) and sale_price > adjusted_cost_base:
        net_gain = (sale_price - total_comm - gst_on_comm - lawyer_fees - staging) - adjusted_cost_base
        if net_gain > 0:
            if is_flip:
                # Anti-Flipping Tax: 100% Inclusion
                flipping_tax = net_gain * (marginal_tax_rate / 100)
            else:
                # Standard Capital Gains: 50% Inclusion
                inclusion_amt = net_gain * 0.50
                cap_gains_tax = inclusion_amt * (marginal_tax_rate / 100)

    # 4. Total Costs
    total_costs = (total_comm + gst_on_comm + penalty + lawyer_fees + adjustments + staging + cap_gains_tax + flipping_tax)
    
    # 5. Net Proceeds
    net_proceeds = sale_price - mort_bal - total_costs
    
    return {
        "price": sale_price,
        "comm": total_comm,
        "gst": gst_on_comm,
        "penalty": penalty,
        "cap_gains_tax": cap_gains_tax,
        "flipping_tax": flipping_tax,
        "fees": lawyer_fees + adjustments + staging,
        "total_costs": total_costs,
        "net": net_proceeds
    }

# --- 4. RESULTS ---
if target_price > 0:
    st.divider()
    
    # A. THE 5-POINT SPECTRUM
    st.subheader("📊 Scenario Spectrum")
    
    scenarios = [
        {"label": "Price Adjusted -10%", "price": target_price * 0.90, "bg": "#FEF2F2", "text": "#7F1D1D"},
        {"label": "Price Adjusted -5%", "price": target_price * 0.95, "bg": "#FFF1F2", "text": "#991B1B"},
        {"label": "Target Price", "price": target_price, "bg": "#FFFBEB", "text": "#92400E"},
        {"label": "Price Adjusted +5%", "price": target_price * 1.05, "bg": "#F0FDF4", "text": "#166534"},
        {"label": "Price Adjusted +10%", "price": target_price * 1.10, "bg": "#DCFCE7", "text": "#14532D"},
    ]
    
    spectrum_html = '<div style="display: flex; width: 100%; border-radius: 12px; overflow: hidden; border: 1px solid #E5E7EB; margin-bottom: 20px;">'
    
    for i, s in enumerate(scenarios):
        res = calculate_proceeds(s['price'])
        border_right = "border-right: 1px solid rgba(0,0,0,0.05);" if i < 4 else ""
        
        spectrum_html += f'<div style="flex: 1; background-color: {s["bg"]}; padding: 15px 5px; text-align: center; {border_right}">'
        spectrum_html += f'<div style="font-size: 0.7em; font-weight: bold; color: {s["text"]}; opacity: 0.8; margin-bottom: 5px; text-transform: uppercase;">{s["label"]}</div>'
        spectrum_html += f'<div style="font-size: 1.1em; font-weight: 700; color: #1F2937; margin-bottom: 8px;">${s["price"]/1000:,.0f}k</div>'
        spectrum_html += f'<div style="font-size: 1.0em; font-weight: 600; color: #DC2626; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 6px; margin-bottom: 6px;">Costs: -${res["total_costs"]/1000:,.1f}k</div>'
        spectrum_html += f'<div style="font-size: 1.3em; font-weight: 800; color: {s["text"]};">${res["net"]/1000:,.0f}k</div>'
        spectrum_html += f'<div style="font-size: 0.65em; color: {s["text"]}; opacity: 0.7;">Net Proceeds</div>'
        spectrum_html += '</div>'
    
    spectrum_html += '</div>'
    st.markdown(spectrum_html, unsafe_allow_html=True)
    st.write("") 

    # B. THE OFFICIAL BREAKDOWN
    target_res = calculate_proceeds(target_price)

    st.subheader("📉 Official Net Sheet (Target Price)")
    
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

    rows_html = ""
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Sale Price</span><span class="net-sheet-val">${target_price:,.2f}</span></div>'
    
    if mort_bal > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Mortgage Discharge</span><span class="net-sheet-val negative">-${mort_bal:,.2f}</span></div>'
    
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Real Estate Commission ({comm_tier1_pct}% / {comm_rem_pct}%)</span><span class="net-sheet-val negative">-${target_res["comm"]:,.2f}</span></div>'
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">GST on Commission (5%)</span><span class="net-sheet-val negative">-${target_res["gst"]:,.2f}</span></div>'
    
    if target_res['penalty'] > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Mortgage Penalty (Est.)</span><span class="net-sheet-val negative">-${target_res["penalty"]:,.2f}</span></div>'
    
    rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Legal & Adjustments</span><span class="net-sheet-val negative">-${target_res["fees"]:,.2f}</span></div>'
    
    # --- SEPARATE LINES FOR TAXES ---
    if target_res['cap_gains_tax'] > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Capital Gains Tax (Est.)</span><span class="net-sheet-val negative">-${target_res["cap_gains_tax"]:,.2f}</span></div>'
    
    if target_res['flipping_tax'] > 0:
        rows_html += f'<div class="net-sheet-row"><span class="net-sheet-label">Anti-Flipping Tax (100% Inclusion)</span><span class="net-sheet-val negative">-${target_res["flipping_tax"]:,.2f}</span></div>'
    
    rows_html += f'<div class="net-sheet-row total"><span class="net-sheet-label">ESTIMATED NET PROCEEDS</span><span class="net-sheet-val positive">${target_res["net"]:,.2f}</span></div>'

    st.markdown(f"""
    <div style="background-color: white; padding: 30px; border-radius: 12px; border: 1px solid #DEE2E6; max-width: 800px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        {rows_html}
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Note: This is an estimate. Penalties and taxes vary based on exact lender terms and CRA assessments.")

else:
    st.info("👈 Enter a target price to generate the analysis.")

show_disclaimer()
