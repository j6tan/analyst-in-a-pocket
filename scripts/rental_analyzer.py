import streamlit as st
import pandas as pd
import numpy as np
import os
from style_utils import inject_global_css, show_disclaimer
from data_handler import init_session_state, load_user_data

# --- 1. CONFIG & AUTH ---
init_session_state()
inject_global_css()

try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="analyst_in_a_pocket_v1")
except Exception:
    geolocator = None

if st.button("⬅️ Back to Home Dashboard"):
    st.switch_page("home.py")
st.divider()

# --- 2. BRANDING ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"

prof = st.session_state.app_db.get('profile', {})
p1_name = prof.get('p1_name', 'Client 1')
p2_name = prof.get('p2_name', 'Client 2')

st.title("Pro Rental Portfolio Analyzer")

# --- 3. GLOBAL SETTINGS PANEL ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    
    # Row 1: Financing Mode
    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True)
    with g_col2:
        m_rate = st.number_input("Mortgage Interest (%)", value=5.1, step=0.1)
    with g_col3:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1)
    
    # Row 2: Management
    g_col4, g_col5, g_col6 = st.columns(3)
    with g_col4:
        use_mgmt = st.checkbox("Use Property Manager?")
    with g_col5:
        mgmt_fee_pct = st.number_input("Management Fee (%)", value=8.0, step=0.5) if use_mgmt else 0.0
    with g_col6:
        st.write("") # Placeholder for alignment

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500, "dp_val": 20.0, "beds": 2, "baths": 2, "year": 2010, "ins": 1200},
    ]

def geocode_address(index):
    if not geolocator: return
    addr = st.session_state.rental_listings[index]['address']
    if addr:
        try:
            location = geolocator.geocode(addr)
            if location:
                st.session_state.rental_listings[index]['lat'] = location.latitude
                st.session_state.rental_listings[index]['lon'] = location.longitude
                st.session_state.rental_listings[index]['address'] = location.address
                st.toast(f"📍 Added to Map: {location.address}")
        except: pass

st.subheader("🏠 Property Listings")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"Listing #{i+1}: {listing['address'][:35] if listing['address'] else 'Empty Address'}", expanded=(i==0)):
        
        # Row 1: Address & Map Button
        r1_c1, r1_c2, r1_c3 = st.columns([4, 1, 1])
        with r1_c1:
            listing['address'] = st.text_input("Property Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed")
        with r1_c2:
            st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3:
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i)
                st.rerun()

        # Row 2: Financials
        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1: listing['price'] = st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}")
        with r2_c2: 
            label = "Down Payment (%)" if dp_mode == "Percentage (%)" else "Down Payment ($)"
            listing['dp_val'] = st.number_input(label, value=listing.get('dp_val', 20.0), key=f"dp_{i}")
        with r2_c3: listing['rent'] = st.number_input("Projected Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}")

        # Row 3: Specs
        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: listing['beds'] = st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}")
        with r3_c2: listing['baths'] = st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}")
        with r3_c3: listing['sqft'] = st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}")
        with r3_c4: listing['year'] = st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}")

        # Row 4: Recurring Costs
        r4_c1, r4_c2, r4_c3 = st.columns(3)
        with r4_c1: listing['tax'] = st.number_input("Annual Property Tax ($)", value=listing['tax'], key=f"tx_{i}")
        with r4_c2: listing['strata'] = st.number_input("Monthly Condo/Strata Fee ($)", value=listing['strata'], key=f"st_{i}")
        with r4_c3: listing['ins'] = st.number_input("Est. Annual Insurance ($)", value=listing.get('ins', 1000), key=f"in_{i}")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Another Listing", on_click=lambda: st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0}))

# --- 5. CALCULATIONS ---
results = []
for l in st.session_state.rental_listings:
    if l['price'] > 0 and l['lat'] != 0.0:
        # Operating Expenses
        mgmt_cost = (l['rent'] * 12 * (mgmt_fee_pct / 100))
        reserves = (l['rent'] * 12 * 0.05) # Professional Vacancy/Maint Reserve
        gross_income = l['rent'] * 12
        operating_expenses = l['tax'] + (l['strata'] * 12) + l['ins'] + mgmt_cost + reserves
        noi = gross_income - operating_expenses
        
        # Financing Logic
        dp_amt = (l['price'] * (l['dp_val'] / 100)) if dp_mode == "Percentage (%)" else l['dp_val']
        loan = l['price'] - dp_amt
        r = (m_rate / 100) / 12
        n = m_amort * 12
        pmt = loan * (r * (1 + r)**n) / ((1 + r)**n - 1) if r > 0 else loan / n
        annual_mortgage = pmt * 12
        net_cashflow = noi - annual_mortgage
        
        results.append({
            "Address": l['address'], "Price": l['price'], "Down Payment": dp_amt,
            "Gross Income": gross_income, "Op Expenses": operating_expenses,
            "Annual Mtg": annual_mortgage, "Cap Rate (%)": (noi / l['price']) * 100,
            "CoC Return (%)": (net_cashflow / dp_amt) * 100 if dp_amt > 0 else 0,
            "Annual Net ($)": net_cashflow, "lat": l['lat'], "lon": l['lon']
        })

# --- 6. OUTPUTS ---
if results:
    df_results = pd.DataFrame(results)
    st.divider()
    st.subheader("🗺️ Portfolio Map")
    st.map(df_results)

    st.subheader("📊 Performance Ranking")
    sort_by = st.radio("Primary Metric:", ["Best CoC Return", "Best Cap Rate", "Highest Cashflow"], horizontal=True)
    sort_key = {"Best CoC Return": "CoC Return (%)", "Best Cap Rate": "Cap Rate (%)", "Highest Cashflow": "Annual Net ($)"}[sort_by]
    df_ranked = df_results.sort_values(by=sort_key, ascending=False)
    
    st.dataframe(
        df_ranked.drop(columns=['lat', 'lon', 'Down Payment', 'Gross Income', 'Op Expenses', 'Annual Mtg']), 
        use_container_width=True, hide_index=True,
        column_config={"Price": st.column_config.NumberColumn(format="$%d"), "Annual Net ($)": st.column_config.NumberColumn(format="$%d"),
                       "Cap Rate (%)": st.column_config.NumberColumn(format="%.2f%%"), "CoC Return (%)": st.column_config.ProgressColumn(min_value=0, max_value=15, format="%.2f%%")}
    )

    # Top Pick Details
    st.subheader("💰 Deep Underwriting (Top Selection)")
    top = df_ranked.iloc[0]
    st.markdown(f"**Selected Listing:** {top['Address']}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Down Payment Required", f"${top['Down Payment']:,.0f}")
    r2.metric("Gross Annual Income", f"${top['Gross Income']:,.0f}")
    r3.metric("Operating Expenses", f"${top['Op Expenses']:,.0f}")
    r4.metric("Annual Mortgage", f"${top['Annual Mtg']:,.0f}")

show_disclaimer()
