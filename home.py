import streamlit as st
import os
import base64
from style_utils import inject_global_css

# Ensure style is injected
inject_global_css()

# --- 1. SESSION CHECK ---
if 'app_db' not in st.session_state:
    st.session_state.app_db = {'profile': {}} 

profile = st.session_state.app_db['profile']

# --- 2. INLINE LOGO & TITLE ---
# Convert image to base64 so it can sit perfectly inside the H1 tag
def get_inline_logo(img_path, width=60):
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        # Flexbox alignment ensures it doesn't get pushed up or down
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; margin-right: 15px; vertical-align: middle;">'
    return "🔥" # Fallback if logo.png is missing

logo_html = get_inline_logo("logo.png", width=65)

# The display: flex ensures the logo and text are perfectly centered together
st.write("")
st.markdown(f"""
    <div style='display: flex; justify-content: center; align-items: center; margin-bottom: 5px;'>
        {logo_html}
        <h1 style='margin: 0; padding: 0;'>FIRE Investor Dashboard</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div style="padding: 0px 15px 20px 15px;">
        <p style='text-align: center; color: #6c757d; font-size: 1.1em; font-style: italic; margin-bottom: 0; line-height: 1.4;'>
            Help Canadian T4 earners save money and reach financial freedom.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- 3. FINANCIAL PASSPORT (Central Info) ---
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

# --- 4. TOOL GRID LOGIC ---
def render_tool_card(title, description, page_path, is_pro=False):
    with st.container(border=True):
        header = f"{title} 💎" if is_pro else title
        st.markdown(f"#### {header}")
        st.write(description)
        
        button_label = "Launch Analysis" if not is_pro else "View Premium Tool"
        if st.button(button_label, key=page_path, use_container_width=True):
            st.switch_page(page_path)

# --- 5. TIER 1: FOUNDATIONS (FREE) ---
st.subheader("🧱 Foundations & Budgeting")
f_c1, f_c2, f_c3 = st.columns(3) 

with f_c1:
    render_tool_card("Monthly Budget", "Define your lifestyle burn rate (Food, Kids, Transport) for accurate planning.", "scripts/budget.py")
with f_c2:
    render_tool_card("Affordability Primary", "Check your maximum mortgage qualification based on T4 income.", "scripts/affordability.py")
with f_c3:
    render_tool_card("Buy vs Rent", "The classic wealth-building comparison for Canadians.", "scripts/buy_vs_rent.py")

st.write("") 

# --- 6. TIER 2: ADVANCED WEALTH STRATEGY (PRO) ---
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

# --- 7. INVESTMENT DEEP DIVES ---
st.subheader("📈 Investment Analysis")
i_c1, i_c2 = st.columns(2)
with i_c1:
    render_tool_card("Secondary Home", "Rental property cashflow and cap rate analyzer.", "scripts/affordability_second.py", is_pro=True)
with i_c2:
    render_tool_card("Rental vs Stock", "Real Estate vs S&P 500 showdown.", "scripts/rental_vs_stock.py", is_pro=True)
