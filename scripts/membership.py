import streamlit as st

st.title("💎 Membership Dashboard")

if st.session_state.get("is_pro", False):
    st.success("✅ Pro Access Active. All professional tools are unlocked.")
    if st.button("Log Out / Test Public View"):
        st.session_state.is_pro = False
        st.rerun()
else:
    st.subheader("Redeem Membership ID")
    member_id = st.text_input("Enter your PRO ID", placeholder="PRO-123")
    
    if st.button("Verify & Unlock Access"):
        if member_id == "PRO-123":
            st.session_state.is_pro = True
            st.success("Access Granted! Navigation updated.")
            st.rerun()
        else:
            st.error("Invalid ID. Try using PRO-123")

st.divider()
st.markdown("### 🚀 Pro Features")
st.write("- **Secondary Property:** Analyze investment property affordability.")
# ... add other features as needed
