import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")
st.title("🕵️ ID Hunter")

# 1. Connect
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    st.success("✅ Connected to Supabase")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# 2. Fetch ANY row to see the real IDs
if st.button("🔎 Show Me The Real IDs"):
    try:
        # We limit to 5 rows and DO NOT filter by "dori" to prevent the crash
        response = supabase.table('user_data').select('*').limit(5).execute()
        
        if response.data:
            st.success("✅ Success! Here is what your database actually contains:")
            
            # Display the raw data so we can see the 'user_id' format
            data = response.data
            for i, row in enumerate(data):
                st.write(f"### Row {i+1}")
                st.write(f"**User ID:** `{row.get('user_id', 'MISSING')}`")
                st.json(row)
                
            st.info("👆 COPY that long 'User ID' code. That is what you must use to log in!")
        else:
            st.warning("⚠️ Connected, but the table 'user_data' is EMPTY.")
            
    except Exception as e:
        # If this fails, the table name 'user_data' is probably wrong
        st.error(f"❌ Database Error: {e}")
        st.write("Check: Is your table named `user_data`? Or maybe `profiles`?")
