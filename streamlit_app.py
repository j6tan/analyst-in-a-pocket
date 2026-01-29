import streamlit as st
import json
import os
import pandas as pd
import pdfplumber
import re
import time

# --- 1. SESSION STATE SETUP ---
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "p1_name": "", "p2_name": "",
        "p1_t4": 0.0, "p1_bonus": 0.0, "p1_commission": 0.0, "p1_pension": 0.0,
        "p2_t4": 0.0, "p2_bonus": 0.0, "p2_commission": 0.0, "p2_pension": 0.0,
        "inv_rental_income": 0.0,
        "car_loan": 0.0, "student_loan": 0.0, "cc_pmt": 0.0, "loc_pmt": 0.0, "loc_balance": 0.0,
        "housing_status": "Renting", "province": "Ontario",
        "m_bal": 0.0, "m_rate": 0.0, "m_amort": 25, "prop_taxes": 4200.0, "rent_pmt": 0.0,
        "heat_pmt": 125.0 
    }

# --- 2. UNIVERSAL FILE HANDLER ---
def universal_statement_parser(uploaded_file):
    """
    Scans CSV or PDF for financial keywords to auto-fill liabilities.
    """
    extracted_data = {"cc_pmt": 0.0, "car_loan": 0.0, "student_loan": 0.0}
    
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            text_blob = df.to_string().upper()
        else:
            with pdfplumber.open(uploaded_file) as pdf:
                text_blob = "".join([page.extract_text() for page in pdf.pages]).upper()

        # --- KEYWORD HEURISTICS (Universal Logic) ---
        
        # 1. Credit Card Payments (Look for Minimum Payment amounts)
        cc_match = re.search(r"(?:MINIMUM|PAYMENT DUE|VISA|MASTERCARD).*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text_blob)
        if cc_match:
            extracted_data["cc_pmt"] = float(cc_match.group(1).replace(',', ''))

        # 2. Car Loans (Common Canadian lenders/keywords)
        car_keywords = ["FORD CREDIT", "TOYOTA FINANCIAL", "CHEVROLET", "AUTO LOAN", "CAR LOAN"]
        if any(k in text_blob for k in car_keywords):
            car_match = re.search(r"(?:AUTO|LOAN|FINANCE).*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text_blob)
            if car_match:
                extracted_data["car_loan"] = float(car_match.group(1).replace(',', ''))

        # 3. Student Loans
        if "NSLSC" in text_blob or "STUDENT LOAN" in text_blob:
            student_match = re.search(r"(?:STUDENT|NSLSC).*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text_blob)
            if student_match:
                extracted_data["student_loan"] = float(student_match.group(1).replace(',', ''))

        return extracted_data

    except Exception as e:
        st.error(f"Parser Error: {e}")
        return extracted_data

# --- 3. APP CONFIG ---
st.set_page_config(layout="wide", page_title="Analyst in a Pocket", page_icon="📊")

# --- 4. NAVIGATION ---
tools = {
    "👤 Client Profile": "MAIN",
    "📊 Affordability Primary": "affordability.py",
    "🏢 Affordability Secondary": "affordability_second.py", 
    "🛡️ Smith Maneuver": "smith_maneuver.py",
    "📉 Mortgage Scenarios": "mortgage_scenario.py",
    "🔄 Renewal Dilemma": "renewal_analysis.py",
    "⚖️ Buy vs Rent": "buy_vs_rent.py",
    "⚖️ Rental vs Stock": "rental_vs_stock.py",
}
selection = st.sidebar.radio("Go to", list(tools.keys()))

# --- 5. PAGE UI ---
if selection == "👤 Client Profile":
    st.title("General Client Information")

    st.subheader("👥 Household Income Details")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.user_profile['p1_name'] = st.text_input("Full Name", value=st.session_state.user_profile['p1_name'])
        st.session_state.user_profile['p1_t4'] = st.number_input("T4 Income", value=float(st.session_state.user_profile['p1_t4']))
    
    with c2:
        st.session_state.user_profile['p2_name'] = st.text_input("Full Name ", value=st.session_state.user_profile['p2_name'])
        st.session_state.user_profile['p2_t4'] = st.number_input("T4 Income ", value=float(st.session_state.user_profile['p2_t4']))

    st.divider()
    
    # --- NEW FILE UPLOAD SECTION ---
    st.subheader("📁 Auto-Fill from Bank Statement")
    st.info("Upload a PDF or CSV statement. The tool will attempt to detect monthly liabilities automatically.")
    
    uploaded_file = st.file_uploader("Upload Statement", type=["pdf", "csv"])
    
    if uploaded_file:
        with st.spinner("Analyzing document..."):
            auto_data = universal_statement_parser(uploaded_file)
            
            # Apply to state
            if auto_data["cc_pmt"] > 0: st.session_state.user_profile['cc_pmt'] = auto_data["cc_pmt"]
            if auto_data["car_loan"] > 0: st.session_state.user_profile['car_loan'] = auto_data["car_loan"]
            if auto_data["student_loan"] > 0: st.session_state.user_profile['student_loan'] = auto_data["student_loan"]
            
            st.success("Analysis complete! Review the fields below.")

    st.divider()
    st.subheader("💳 Monthly Liabilities")

    l1, l2, l3 = st.columns(3)
    with l1:
        st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments", value=float(st.session_state.user_profile['car_loan']))
        st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments", value=float(st.session_state.user_profile['cc_pmt']))
        st.session_state.user_profile['loc_balance'] = st.number_input("Total LOC Balance", value=float(st.session_state.user_profile['loc_balance']))
    with l3:
        prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
        st.session_state.user_profile['province'] = st.selectbox("Province", prov_options, index=prov_options.index(st.session_state.user_profile.get('province', 'Ontario')))

    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button("💾 Download Profile", data=profile_json, file_name="client_profile.json", mime="application/json")

# --- 6. HANDLE OTHER PAGES ---
else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())
