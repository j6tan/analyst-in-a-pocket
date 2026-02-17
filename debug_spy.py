import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")
st.title("🕵️ Data Spy")

# 1. Direct Connection (No Data Handler)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    st.success("✅ Connected to Supabase directly.")
except Exception as e:
    st.error(f"❌ Connection Failed: {e}")
    st.stop()

# 2. Input to Test
target_user = st.text_input("Enter User ID to Search:", value="dori")

if st.button("🔎 Inspect Raw DB Data"):
    # A. Search Exact Match
    st.write(f"Attempting to fetch data for: `{target_user}`...")
    
    response = supabase.table('user_data').select('*').eq('user_id', target_user).execute()
    
    # B. Display Raw Results
    if response.data and len(response.data) > 0:
        row = response.data[0]
        st.success("✅ Found a Row!")
        
        st.subheader("Raw Database Row:")
        st.json(row)  # <--- THIS IS WHAT I NEED TO SEE
        
        st.subheader("Data Column Structure:")
        data_col = row.get('data')
        if data_col:
            st.json(data_col) # <--- THIS IS CRITICAL
        else:
            st.warning("⚠️ The 'data' column is NULL or Empty.")
    else:
        st.error(f"❌ No row found for '{target_user}'.")
        
        # C. list all users to see if there's a mismatch
        st.write("---")
        st.write("Listing ALL users in DB to check for typos:")
        all_users = supabase.table('user_data').select('user_id').execute()
        st.write([u['user_id'] for u in all_users.data])
