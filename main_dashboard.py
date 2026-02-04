import streamlit as st

st.title("🚀 Analyst in a Pocket: Dashboard")

# --- TOP PANEL: THE FINANCIAL PASSPORT ---
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### 👤 Financial Passport: {st.session_state.user_profile['p1_name']}")
        status = "✅ Complete" if st.session_state.user_profile['setup_complete'] else "⚠️ Incomplete"
        st.write(f"**Current Status:** {status} | **Income:** ${st.session_state.user_profile['p1_t4']:,.0f}")
    with col2:
        # CLICKABLE LINK TO PROFILE
        if st.button("Update Info", use_container_width=True):
            st.switch_page("scripts/profile.py")

st.divider()

# --- TOOL GRID (DESIGN OPTION B) ---
st.subheader("🏠 Foundations (Free)")
col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("#### 📊 Affordability")
        st.write("Calculate your max mortgage based on current T4 income.")
        if st.button("Launch Tool", key="nav_afford", use_container_width=True):
            st.switch_page("scripts/affordability.py")

with col2:
    with st.container(border=True):
        st.markdown("#### ⚖️ Buy vs. Rent")
        st.write("Determine if renting or buying is better for your FIRE timeline.")
        if st.button("Launch Tool", key="nav_bvr", use_container_width=True):
            st.switch_page("scripts/buy_vs_rent.py")

st.divider()

st.subheader("🚀 Advanced Strategy (Tier 2)")
a_col1, a_col2 = st.columns(2)

with a_col1:
    with st.container(border=True):
        st.markdown("#### 🛡️ Smith Maneuver 🔒")
        st.caption("Strategic tax-deductible mortgage conversion.")
        st.button("Upgrade to Unlock ($15/mo)", type="primary", use_container_width=True)
