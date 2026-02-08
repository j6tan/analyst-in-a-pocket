import streamlit as st
from style_utils import inject_global_css

# Ensure style is injected
inject_global_css()

# --- 1. DATA CONNECTION ---
# We use the new 'app_db' structure we built. 
# If it's missing, we default to empty dict to prevent crashes.
if 'app_db' not in st.session_state:
    st.session_state.app_db = {'profile': {}}

profile = st.session_state.app_db.get('profile', {})

st.title("📊 FIRE Investor Dashboard")

# --- 2. FINANCIAL PASSPORT (Restored) ---
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        # data fetching from the new DB structure
        name = profile.get('p1_name') or "Investor"
        income = float(profile.get('p1_t4', 0)) + float(profile.get('p2_t4', 0))
        province = profile.get('province', 'Ontario')
        
        st.markdown(f"### 👤 {name}'s Financial Passport")
        st.write(f"**Total Household Income:** ${income:,.0f} | **Province:** {province}")
    with col2:
        if st.button("Manage Profile", use_container_width=True):
            st.switch_page("scripts/profile.py")

st.divider()

# --- 3. TOOL GRID LOGIC ---
def render_tool_card(title, description, page_path, is_pro=False):
    with st.container(border=True):
        # Add visual indicators for Pro tools
        header = f"{title} 🔒" if is_pro else title
        st.markdown(f"#### {header}")
        st.write(description)
        
        # Determine button style
        button_type = "primary" if not is_pro else "secondary"
        button_label = "Launch Analysis" if not is_pro else "Premium Tool"
        
        if st.button(button_label, key=page_path, use_container_width=True, type=button_type):
            st.switch_page(page_path)

# --- 4. TIER 1: FOUNDATIONS (FREE) ---
st.subheader("🧱 Foundations & Budgeting")
f_c1, f_c2 = st.columns(2)
with f_c1:
    render_tool_card(
        "Affordability Primary", 
        "Check your maximum mortgage qualification based on T4 income.", 
        "scripts/affordability.py"
    )
with f_c2:
    render_tool_card(
        "Buy vs Rent", 
        "The classic wealth-building comparison for Canadians.", 
        "scripts/buy_vs_rent.py"
    )

st.write("") # Spacing

# --- 5. TIER 2: ADVANCED WEALTH STRATEGY (PRO) ---
st.subheader("🚀 Advanced Strategy (Premium)")
st.info("Unlock these tools to optimize for Financial Independence.")

p_c1, p_c2, p_c3 = st.columns(3)

with p_c1:
    render_tool_card(
        "Smith Maneuver", 
        "Convert mortgage interest into tax-deductions.", 
        "scripts/smith_maneuver.py", 
        is_pro=True
    )
with p_c2:
    render_tool_card(
        "Mortgage Scenarios", 
        "Model prepayments vs. market investing.", 
        "scripts/mortgage_scenario.py", 
        is_pro=True
    )
with p_c3:
    render_tool_card(
        "Renewal Dilemma", 
        "Should you switch lenders or stay?", 
        "scripts/renewal_scenario.py", 
        is_pro=True
    )

st.divider()

# --- 6. INVESTMENT DEEP DIVES ---
st.subheader("📈 Investment Analysis")
i_c1, i_c2 = st.columns(2)
with i_c1:
    render_tool_card(
        "Secondary Home", 
        "Rental property cashflow and cap rate analyzer.", 
        "scripts/affordability_second.py", 
        is_pro=True
    )
with i_c2:
    render_tool_card(
        "Rental vs Stock", 
        "Real Estate vs S&P 500 showdown.", 
        "scripts/rental_vs_stock.py", 
        is_pro=True
    )
