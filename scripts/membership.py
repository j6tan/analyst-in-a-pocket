import streamlit as st

st.title("💎 Pro Membership")

if st.session_state.get("is_pro", False):
    st.success(f"Verified Pro Account: {st.session_state.username}")
    st.markdown("### ✨ You have full access")
    st.write("All locks have been removed. You can now use the Smith Manoeuvre, Renewal Scenarios, and more.")
    
    if st.button("Log Out"):
        st.session_state.is_logged_in = False
        st.session_state.is_pro = False
        st.rerun()
else:
    st.subheader("Upgrade to Analyst Pro")
    st.write("Get the full power of the suite for $19/mo.")
    
    # This is where your future Stripe button goes
    st.button("Subscribe with Credit Card", use_container_width=True)
    
    st.info("💡 Already a member? Use the login form in the sidebar to unlock your tools.")
