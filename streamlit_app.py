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

# --- 2. UNIVERSAL PARSER LOGIC ---
def universal_statement_parser(uploaded_file):
    extracted_data = {"cc_pmt": 0.0, "car_loan": 0.0, "student_loan": 0.0}
    text_blob = ""
    
    try:
        # Check file type and extract text/data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
            text_blob = df.to_string().upper()
        
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            # Read all sheets and combine them into a single searchable string
            excel_data = pd.read_excel(uploaded_file, sheet_name=None)
            text_blob = " ".join([df.to_string().upper() for df in excel_data.values()])
            
        elif uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                text_blob = " ".join([page.extract_text() for page in pdf.pages if page.extract_text()]).upper()

        # --- KEYWORD SEARCH (REGEX) ---
        # 1. Credit Card (Minimum Payments)
        cc_patterns = [r"MINIMUM PAYMENT.*?(\d[\d,.]*)", r"PAYMENT DUE.*?(\d[\d,.]*)", r"TOTAL MINIMUM.*?(\d[\d,.]*)"]
        for p in cc_patterns:
            match = re.search(p, text_blob)
            if match:
                extracted_data["cc_pmt"] = float(match.group(1).replace(',', ''))
                break

        # 2. Car Loans
        car_keywords = ["FORD CREDIT", "TOYOTA FINANCIAL", "CHEVROLET", "AUTO LOAN", "GMF", "CAR LOAN"]
        if any(k in text_blob for k in car_keywords):
            car_match = re.search(r"(?:AUTO|LOAN|FINANCE|DEBIT).*?(\d[\d,.]*)", text_blob)
            if car_match:
                extracted_data["car_loan"] = float(car_match.group(1).replace(',', ''))

        # 3. Student Loans
        if any(k in text_blob for k in ["NSLSC", "STUDENT LOAN", "OSAP"]):
            student_match = re.search(r"(?:STUDENT|NSLSC|OSAP).*?(\d[\d,.]*)", text_blob)
            if student_match:
                extracted_data["student_loan"] = float(student_match.group(1).replace(',', ''))

        return extracted_data
    except Exception as e:
        st.error(f"Analysis failed: {e}")
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

    st.subheader("📁 Auto-Fill Statement Data")
    # Added xls and xlsx to the allowed types
    uploaded_file = st.file_uploader(
        "Upload a Bank Statement (PDF, CSV, or Excel)", 
        type=["pdf", "csv", "xls", "xlsx"], 
        help="Upload a document to automatically extract credit card and loan payments."
    )
    
    if uploaded_file:
        with st.spinner("Scanning Document..."):
            auto_data = universal_statement_parser(uploaded_file)
            
            if any(v > 0 for v in auto_data.values()):
                # Only update fields where we found a value > 0
                for k, v in auto_data.items():
                    if v > 0:
                        st.session_state.user_profile[k] = v
                st.success("Success! We found matching liabilities and updated the fields below.")
            else:
                st.warning("Document scanned, but no specific liabilities were found. You can still enter them manually.")

    st.divider()

    # --- INPUT FIELDS (SAME AS BEFORE) ---
    st.subheader("👥 Household Income Details")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Primary Client")
        st.session_state.user_profile['p1_name'] = st.text_input("Full Name", value=st.session_state.user_profile['p1_name'])
        st.session_state.user_profile['p1_t4'] = st.number_input("T4 Income", value=float(st.session_state.user_profile['p1_t4']))
    
    with c2:
        st.markdown("### Co-Owner / Partner")
        st.session_state.user_profile['p2_name'] = st.text_input("Full Name ", value=st.session_state.user_profile['p2_name'])
        st.session_state.user_profile['p2_t4'] = st.number_input("T4 Income ", value=float(st.session_state.user_profile['p2_t4']))

    st.divider()
    st.subheader("💳 Monthly Liabilities")
    l1, l2, l3 = st.columns(3)
    with l1:
        st.session_state.user_profile['car_loan'] = st.number_input("Car Loan Payments", value=float(st.session_state.user_profile['car_loan']))
        st.session_state.user_profile['student_loan'] = st.number_input("Student Loan Payments", value=float(st.session_state.user_profile['student_loan']))
    with l2:
        st.session_state.user_profile['cc_pmt'] = st.number_input("Credit Card Payments (Min)", value=float(st.session_state.user_profile['cc_pmt']))
        st.session_state.user_profile['loc_balance'] = st.number_input("Total LOC Balance", value=float(st.session_state.user_profile['loc_balance']))
    with l3:
        prov_options = ["Ontario", "BC", "Alberta", "Quebec", "Manitoba", "Saskatchewan", "Nova Scotia", "NB", "PEI", "NL"]
        st.session_state.user_profile['province'] = st.selectbox("Province", prov_options, index=prov_options.index(st.session_state.user_profile.get('province', 'Ontario')))

    profile_json = json.dumps(st.session_state.user_profile, indent=4)
    st.download_button("💾 Download Profile", data=profile_json, file_name="client_profile.json", mime="application/json")

# --- 6. PAGE REDIRECTION ---
else:
    file_path = os.path.join("scripts", tools[selection])
    if os.path.exists(file_path):
        exec(open(file_path, encoding="utf-8").read(), globals())
