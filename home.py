import streamlit as st
from style_utils import inject_global_css

# Inject styles
inject_global_css()

# --- DASHBOARD ---
st.title("📊 Analyst in a Pocket")
st.markdown("### Welcome to your wealth strategy dashboard.")

# Basic status check
if 'is_logged_in' in st.session_state and st.session_state.is_logged_in:
    st.success(f"You are logged in as **{st.session_state.username}**. Your data is saving to the cloud.")
else:
    st.info("You are in **Guest Mode**. Data will disappear when you close this tab.")

st.divider()

# Quick Links
c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.subheader("👤 Profile")
        st.write("Update your income and details.")
        if st.button("Go to Profile"):
            st.switch_page("scripts/profile.py")

with c2:
    with st.container(border=True):
        st.subheader("🛡️ Smith Maneuver")
        st.write("Tax-deductible mortgage strategy.")
        if st.button("Go to Calculator"):
            st.switch_page("scripts/smith_maneuver.py")

with c3:
    with st.container(border=True):
        st.subheader("🤔 Buy vs Rent")
        st.write("Compare housing options.")
        if st.button("Compare Now"):
            st.switch_page("scripts/buy_vs_rent.py")
