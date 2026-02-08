import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from style_utils import inject_global_css

# 1. Inject the Wealthsimple-inspired Editorial CSS
inject_global_css()

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 1. THEME & BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. DATA RETRIEVAL (GLOBAL PROFILE) ---
prof = st.session_state.app_db.get('profile', {})
name1 = prof.get('p1_name') or "Primary Client"
name2 = prof.get('p2_name') or ""
household = f"{name1} and {name2}" if name2 else name1

# --- 3. PERSISTENCE INITIALIZATION ---
if "aff_rent_store" not in st.session_state:
    # Grab rent from profile, or default to 2500 if missing
    profile_rent = float(prof.get('current_rent', 2500.0))
    
    st.session_state.aff_rent_store = {
        "price": 800000, "dp": 200000, "rate": 4.0, "ann_tax": 2000,
        "mo_maint": 500, "apprec": 1.5, "rent": 3000, "rent_inc": 2.5,
        "stock_ret": 8.0, "years": 15
    }

store = st.session_state.aff_rent_store

# --- 4. CALCULATION ENGINE ---
def run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years):
    loan = price - dp
    m_rate = (rate/100)/12
    n_months = 25 * 12
    monthly_pi = loan * (m_rate * (1+m_rate)**n_months) / ((1+m_rate)**n_months - 1)
    
    data = []
    total_owner_unrecoverable = 0
    total_renter_unrecoverable = 0
    curr_loan = loan
    curr_val = price
    curr_rent = rent
    renter_portfolio = dp 
    
    for y in range(1, years + 1):
        annual_int = 0
        for _ in range(12):
            mo_interest = curr_loan * m_rate
            mo_principal = monthly_pi - mo_interest
            annual_int += mo_interest
            curr_loan -= mo_principal

        owner_lost_this_year = annual_int + ann_tax + (mo_maint * 12)
        total_owner_unrecoverable += owner_lost_this_year
        curr_val *= (1 + apprec/100)
        selling_costs = (curr_val * 0.03) + 1500
        owner_wealth_net = curr_val - max(0, curr_loan) - selling_costs
        total_renter_unrecoverable += curr_rent * 12
        owner_mo_outlay = monthly_pi + (ann_tax/12) + mo_maint
        mo_savings_gap = owner_mo_outlay - curr_rent
        
        for _ in range(12):
            renter_portfolio = (renter_portfolio + mo_savings_gap) * (1 + (stock_ret/100)/12)

        data.append({
            "Year": y, "Owner Net Wealth": owner_wealth_net, "Renter Wealth": renter_portfolio,
            "Owner Unrecoverable": total_owner_unrecoverable, "Renter Unrecoverable": total_renter_unrecoverable
        })
        curr_rent *= (1 + rent_inc/100)
    return pd.DataFrame(data)

# --- 5. HEADER & STORY ---
st.markdown("<style>div.block-container {padding-top: 1rem;}</style>", unsafe_allow_html=True)
header_col1, header_col2 = st.columns([1, 5], vertical_alignment="center")
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=140)
with header_col2:
    st.title("Buy vs. Rent Analysis")

st.markdown(f"""
<div style="background-color: {OFF_WHITE}; padding: 15px 25px; border-radius: 10px; border: 1px solid {BORDER_GREY}; border-left: 8px solid {PRIMARY_GOLD}; margin-bottom: 20px;">
    <h3 style="color: {SLATE_ACCENT}; margin: 0 0 10px 0; font-size: 1.5em;">🛑 {household}: The Homebuyer's Dilemma</h3>
    <p style="color: {SLATE_ACCENT}; font-size: 1.1em; line-height: 1.4; margin: 0;">
        {name1} values the <b>equity growth</b> of ownership, while {name2 if name2 else 'the household'} is focused on the <b>opportunity cost</b> of the stock market. 
        We have analyzed your break-even horizon and wealth trajectory below.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 6. INPUTS ---
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("🏠 Homeownership Path")
    price = st.number_input("Purchase Price ($)", value=store['price'], step=50000, key="br_price")
    dp = st.number_input("Down Payment ($)", value=store['dp'], step=10000, key="br_dp")
    rate = st.number_input("Mortgage Rate (%)", value=store['rate'], step=0.1, key="br_rate")
    ann_tax = st.number_input("Annual Property Tax ($)", value=store['ann_tax'], step=100, key="br_tax")
    mo_maint = st.number_input("Monthly Maintenance ($)", value=store['mo_maint'], step=50, key="br_maint")
    apprec = st.number_input("Annual Appreciation (%)", value=store['apprec'], step=0.5, key="br_apprec")

with col_right:
    st.subheader("🏢 Rental Path")
    rent = st.number_input("Current Monthly Rent ($)", value=store['rent'], step=100, key="br_rent")
    rent_inc = st.number_input("Annual Rent Increase (%)", value=store['rent_inc'], step=0.5, key="br_rent_inc")
    stock_ret = st.number_input("Target Stock Return (%)", value=store['stock_ret'], step=0.5, key="br_stock")
    years = st.number_input("Analysis Horizon (Years)", value=store['years'], step=5, key="br_years")

st.session_state.aff_rent_store.update({
    "price": price, "dp": dp, "rate": rate, "ann_tax": ann_tax, 
    "mo_maint": mo_maint, "apprec": apprec, "rent": rent, 
    "rent_inc": rent_inc, "stock_ret": stock_ret, "years": years
})

df = run_wealth_comparison(price, dp, rate, apprec, ann_tax, mo_maint, rent, rent_inc, stock_ret, years)

# --- 7. VISUALS ---
owner_unrec, renter_unrec = df['Owner Unrecoverable'].iloc[-1], df['Renter Unrecoverable'].iloc[-1]
owner_wealth, renter_wealth = df['Owner Net Wealth'].iloc[-1], df['Renter Wealth'].iloc[-1]

st.subheader("📊 Performance Comparison")
v_col1, v_col2 = st.columns(2)

with v_col1:
    fig_unrec = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_unrec], marker_color=PRIMARY_GOLD, text=[f"${owner_unrec:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_unrec], marker_color=CHARCOAL, text=[f"${renter_unrec:,.0f}"], textposition='auto')
    ])
    fig_unrec.update_layout(
        # FIX: Added xanchor='center' to ensure it sits exactly in the middle
        title=dict(text="Total Sunk Costs", x=0.5, xanchor='center', font=dict(size=18)),
        yaxis=dict(tickformat="$,.0f"),
        height=300,
        margin=dict(t=40, b=0, l=40, r=40),
        showlegend=False
    )
    st.plotly_chart(fig_unrec, use_container_width=True, config={'displayModeBar': False})
    st.markdown("<p style='text-align: center; color: #6c757d; font-size: 0.8em; margin-top: -10px;'>Lower is better. Interest/Tax vs. Total Rent.</p>", unsafe_allow_html=True)

with v_col2:
    fig_wealth = go.Figure(data=[
        go.Bar(name='Homeowner', x=['Homeowner'], y=[owner_wealth], marker_color=PRIMARY_GOLD, text=[f"${owner_wealth:,.0f}"], textposition='auto'),
        go.Bar(name='Renter', x=['Renter'], y=[renter_wealth], marker_color=CHARCOAL, text=[f"${renter_wealth:,.0f}"], textposition='auto')
    ])
    fig_wealth.update_layout(
        # FIX: Added xanchor='center' here as well
        title=dict(text="Final Net Worth", x=0.5, xanchor='center', font=dict(size=18)),
        yaxis=dict(tickformat="$,.0f"),
        height=300,
        margin=dict(t=40, b=0, l=40, r=40),
        showlegend=False
    )
    st.plotly_chart(fig_wealth, use_container_width=True, config={'displayModeBar': False})
    st.markdown(f"<p style='text-align: center; color: #6c757d; font-size: 0.8em; margin-top: -10px;'>Total wealth after {years} years.</p>", unsafe_allow_html=True)

# --- 8. STRATEGIC ANALYST VERDICT ---
st.divider()
st.subheader("🎯 Strategic Wealth Verdict")
ins_col1, ins_col2 = st.columns(2)

with ins_col1:
    if owner_wealth > renter_wealth:
        st.success(f"🏆 **Wealth Champion: Homeowner**\n\nOwnership builds **${(owner_wealth - renter_wealth):,.0f} more** in assets over {years} years.")
    else:
        st.warning(f"🏆 **Wealth Champion: Renter**\n\nStock returns currently outperform equity. The Renter is **${(renter_wealth - owner_wealth):,.0f} ahead**.")

    sunk_diff = abs(owner_unrec - renter_unrec)
    if owner_unrec < renter_unrec:
        st.info(f"✨ **Efficiency Champion: Homeowner**\n\nOwnership is **${sunk_diff:,.0f} cheaper** in 'dead money' lost than renting equivalent housing.")
    else:
        st.info(f"✨ **Efficiency Champion: Renter**\n\nRenting is **${sunk_diff:,.0f} cheaper** in pure cash-out costs than home maintenance/interest.")

with ins_col2:
    if (renter_wealth > owner_wealth) and (owner_unrec < renter_unrec):
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 8px; border: 1px solid #d1d5db;">
        <b>🔍 The Investor's Paradox:</b><br>
        Even though the Homeowner lives more 'efficiently' (lower sunk costs), the Renter is wealthier. 
        <br><br>
        This happens because your <b>{stock_ret}% Stock Return</b> is working harder on your initial capital than your <b>{apprec}% Home Appreciation</b>. You are paying for the luxury of capital growth with higher monthly rent.
        </div>
        """, unsafe_allow_html=True)
    else:
        ahead_mask = df['Owner Net Wealth'] > df['Renter Wealth']
        be_year = int(df[ahead_mask].iloc[0]['Year']) if ahead_mask.any() else None
        if be_year:
            st.write(f"**Break-Even Horizon:** Year {be_year}. This is when equity build-up finally overcomes the high friction costs of interest and taxes.")
        else:
            st.write("**Growth Outlook:** Under current market settings, the 'Opportunity Cost' of the down payment prevents the home from catching up in net worth.")

# --- 9. IDENTICAL ERRORS AND OMISSIONS DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
    <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
        <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
        This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
        This does not constitute financial, legal, or tax advice. Mortgage approval and final figures are subject to lender policy, 
        creditworthiness, and current market conditions. Consult with a professional before making significant financial decisions.
    </p>
</div>
""", unsafe_allow_html=True)


st.caption("Analyst in a Pocket | Strategic Wealth Hub")



