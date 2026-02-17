import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")
st.title("🕵️ Schema Inspector")

# 1. Connect
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    st.success("✅ Connected to Supabase API")
except Exception as e:
    st.error(f"❌ Connection Failed: {e}")
    st.stop()

# 2. Test Table Existence & Structure
st.subheader("Database Diagnosis")

table_name = st.text_input("Table to inspect:", value="user_data")

if st.button("🔬 Inspect Table Structure"):
    try:
        # A. Try to fetch just 1 row (No ID filter, so it won't crash on bad IDs)
        st.info(f"Attempting to read 1 row from '{table_name}'...")
        response = supabase.table(table_name).select("*").limit(1).execute()
        
        # B. Analyze Results
        st.success(f"✅ Success! Table '{table_name}' exists.")
        
        if response.data and len(response.data) > 0:
            row = response.data[0]
            st.write("### 📋 Columns Found:")
            st.json(list(row.keys())) # Show me the column names
            
            st.write("### 🧪 Sample Data (First Row):")
            st.json(row)
            
            # C. Check specifically for 'user_id'
            if 'user_id' in row:
                st.write(f"ℹ️ `user_id` format in DB: `{row['user_id']}`")
                st.write(f"ℹ️ Your input was: `dori`")
                if len(str(row['user_id'])) > 20 and "dori" in "dori":
                    st.warning("⚠️ MISMATCH DETECTED: The database uses UUIDs (long codes), but you are logging in with a short username ('dori'). You must update your 'VALID_USERS' list in `streamlit_app.py` to match these UUIDs.")
            else:
                st.error("❌ The column `user_id` DOES NOT EXIST. Please check the 'Columns Found' list above for the correct ID column name.")
                
        else:
            st.warning(f"⚠️ Table '{table_name}' exists but is EMPTY. Please add a row in Supabase dashboard first.")
            
    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.markdown("""
        **Likely Causes:**
        1. The table name is wrong (Check Supabase Dashboard).
        2. Row Level Security (RLS) is on and blocking access.
        """)
