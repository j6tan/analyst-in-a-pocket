import streamlit as st
import os
from style_utils import inject_global_css

# Ensure style is injected
inject_global_css()

# --- 1. SESSION CHECK ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {'profile': {}} 

profile = st.session_state.app_db['profile']

# --- LOGO INJECTION ---
st.write("") 
if os.path.exists("logo.png"):
    pad_left, logo_col, pad_right = st.columns([4, 3, 4])
    with logo_col:
        st.image("logo.png", use_container_width=True)
else:
    st.markdown("<h2 style='text-align: center; color: #CEB36F;'>🔥 FIRE Calculator</h2>", unsafe_allow_html=True)

# Main Title & Slogan (Fixed Corrupted Emojis)
st.markdown("<h1 style='text-align: center;'>📊 FIRE Investor Dashboard</h1>", unsafe_allow_html=True)
st.markdown("""
    <div style="padding: 0px 15px 20px 15px;">
        <p style='text-align: center; color: #6c757d; font-size: 1.1em; font-style: italic; margin-bottom: 0; line-height: 1.4;'>
            Help Canadian T4 earners save money and reach financial freedom.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- 2. FINANCIAL PASSPORT (Central Info) ---
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        name = profile.get('p1_name') or "Investor"
        income = profile.get('p1_t4', 0) + profile.get('p2_t4', 0)
        st.markdown(f"### 🛂 {name}'s Financial Passport")
        st.write(f"**Total Household Income:** ${income:,.0f} | **Province:** {profile.get('province')}")
    with col2:
        if st.button("Manage Profile", use_container_width=True):
            st.switch_page("scripts/profile.py")

st.divider()

# --- 3. TOOL GRID LOGIC ---
def render_tool_card(title, description, page_path, is_pro=False):
    with st.container(border=True):
        header = f"{title} 💎" if is_pro else title
        st.markdown(f"#### {header}")
        st.write(description)
        
        button_label = "Launch Analysis" if not is_pro else "View Premium Tool"
        if st.button(button_label, key=page_path, use_container_width=True):
            st.switch_page(page_path)

# --- 4. TIER 1: FOUNDATIONS (FREE) ---
st.subheader("🧱 Foundations & Budgeting")
f_c1, f_c2, f_c3 = st.columns(3) 

with f_c1:
    render_tool_card("Monthly Budget", "Define your lifestyle burn rate (Food, Kids, Transport) for accurate planning.", "scripts/budget.py")
with f_c2:
    render_tool_card("Affordability Primary", "Check your maximum mortgage qualification based on T4 income.", "scripts/affordability.py")
with f_c3:
    render_tool_card("Buy vs Rent", "The classic wealth-building comparison for Canadians.", "scripts/buy_vs_rent.py")

st.write("") 

# --- 5. TIER 2: ADVANCED WEALTH STRATEGY (PRO) ---
st.subheader("♟️ Advanced Strategy (Premium)")
st.info("Unlock these tools to optimize for Financial Independence.")

p_c1, p_c2, p_c3 = st.columns(3)

with p_c1:
    render_tool_card("Smith Maneuver", "Convert mortgage interest into tax-deductions.", "scripts/smith_maneuver.py", is_pro=True)
with p_c2:
    render_tool_card("Mortgage Scenarios", "Model prepayments vs. market investing.", "scripts/mortgage_scenario.py", is_pro=True)
with p_c3:
    render_tool_card("Renewal Dilemma", "Should you switch lenders or stay?", "scripts/renewal_analysis.py", is_pro=True)

st.divider()

# --- 6. INVESTMENT DEEP DIVES ---
st.subheader("📈 Investment Analysis")
i_c1, i_c2 = st.columns(2)
with i_c1:
    render_tool_card("Secondary Home", "Rental property cashflow and cap rate analyzer.", "scripts/affordability_second.py", is_pro=True)
with i_c2:
    render_tool_card("Rental vs Stock", "Real Estate vs S&P 500 showdown.", "scripts/rental_vs_stock.py", is_pro=True)
