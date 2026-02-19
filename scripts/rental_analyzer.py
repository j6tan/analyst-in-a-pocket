import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk 
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

# --- 2. BRANDING COLORS (RGBA for Pydeck) ---
PRIMARY_GOLD = [206, 179, 111, 255] # #CEB36F
CHARCOAL = [46, 43, 40, 255]       # #2E2B28
OFF_WHITE = "#F8F9FA"

st.title("Pro Rental Portfolio Analyzer")

# --- 3. GLOBAL SETTINGS PANEL ---
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    
    # Financing & Centralized Down Payment
    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1.5, 1, 1])
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True)
    with g_col2:
        dp_global_val = st.number_input(f"Down Payment ({'%' if 'Percent' in dp_mode else '$'})", 
                                        value=20.0 if "Percent" in dp_mode else 100000.0)
    with g_col3:
        m_rate = st.number_input("Mortgage Interest Rate (%)", value=5.1, step=0.1)
    with g_col4:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1)
    
    # Management Fee
    g_col5, g_col6 = st.columns([2, 1])
    with g_col5:
        use_mgmt = st.checkbox("Will you use a Property Manager?")
    with g_col6:
        mgmt_fee = st.number_input("Management Fee (%)", value=8.0, step=0.5) if use_mgmt else 0.0

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500, "beds": 2, "baths": 2, "year": 2010, "ins": 100, "sqft": 850},
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
                st.rerun() # Refresh to update map immediately
        except: pass

st.subheader("🏠 Property Underwriting")

for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"Listing #{i+1}: {listing['address'][:30]}...", expanded=(i==len(st.session_state.rental_listings)-1)):
        
        # Row 1: Address, Add to Map, Remove
        r1_c1, r1_c2, r1_c3 = st.columns([1.6, 1, 1])
        with r1_c1:
            listing['address'] = st.text_input("Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed")
        with r1_c2:
            st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3:
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i); st.rerun()

        # Row 2: Price, Beds, Baths, Sqft, Year
        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns([2.6, 0.6, 0.6, 1, 1])
        with r2_c1: listing['price'] = st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}")
        with r2_c2: listing['beds'] = st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}")
        with r2_c3: listing['baths'] = st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}")
        with r2_c4: listing['sqft'] = st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}")
        with r2_c5: listing['year'] = st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}")

        # Row 3: Rent, Tax, Strata, Insurance
        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: listing['rent'] = st.number_input("Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}")
        with r3_c2: listing['tax'] = st.number_input("Property Tax ($)", value=listing['tax'], key=f"tx_{i}")
        with r3_c3: listing['strata'] = st.number_input("Strata Fees ($)", value=listing['strata'], key=f"st_{i}")
        with r3_c4: listing['ins'] = st.number_input("Monthly Insurance ($)", value=listing.get('ins', 100), key=f"in_{i}")

if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Another Listing", on_click=lambda: st.session_state.rental_listings.append({"address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0}))

# --- 5. CALCULATIONS ENGINE ---
map_data_list = []
financial_results = []

for idx, l in enumerate(st.session_state.rental_listings):
    if l.get('lat') and l.get('lon'):
        # 1. Prepare Map Data (Always saved if pinned)
        map_entry = {"Address": l['address'], "lat": l['lat'], "lon": l['lon'], "index": idx}
        
        # 2. Prepare Financial Data (Only if Price > 0)
        if l['price'] > 0:
            mgmt_cost = (l['rent'] * 12 * (mgmt_fee / 100))
            reserves = (l['rent'] * 12 * 0.05) 
            gross_inc = l['rent'] * 12
            op_ex = l['tax'] + (l['strata'] * 12) + (l['ins'] * 12) + mgmt_cost + reserves
            noi = gross_inc - op_ex
            
            dp_amt = (l['price'] * (dp_global_val / 100)) if "Percent" in dp_mode else dp_global_val
            loan = l['price'] - dp_amt
            r = (m_rate / 100) / 12
            pmt = loan * (r * (1 + r)**(m_amort*12)) / ((1 + r)**(m_amort*12) - 1) if r > 0 else loan / (m_amort*12)
            net_cf = noi - (pmt * 12)
            
            analysis = {
                "Address": l['address'], "Price": l['price'], "DP": dp_amt, 
                "Gross": gross_inc, "OpEx": op_ex, "Mtg": pmt*12, 
                "Cap Rate %": (noi / l['price']) * 100, 
                "CoC %": (net_cf / dp_amt) * 100 if dp_amt > 0 else 0, 
                "Net $": net_cf, "lat": l['lat'], "lon": l['lon']
            }
            financial_results.append(analysis)
            map_entry.update(analysis) # Merge for map tooltip
            
        map_data_list.append(map_entry)

# --- 6. VISUALS & RANKING ---
if map_data_list:
    df_map = pd.DataFrame(map_data_list)
    df_ranked = pd.DataFrame(financial_results)
    
    st.divider()
    st.subheader("🗺️ Geographic Portfolio Distribution")
    
    # Logic: Differentiate #1 Rank
    best_addr = ""
    if not df_ranked.empty:
        # Default Rank by CoC %
        df_ranked = df_ranked.sort_values(by="CoC %", ascending=False).reset_index(drop=True)
        best_addr = df_ranked.iloc[0]['Address']
    
    df_map['color'] = df_map['Address'].map(lambda x: PRIMARY_GOLD if x == best_addr and best_addr != "" else CHARCOAL)
    df_map['radius'] = df_map['Address'].map(lambda x: 250 if x == best_addr else 150)

    # Pydeck Multi-Pin Rendering
    view_state = pdk.ViewState(latitude=df_map['lat'].mean(), longitude=df_map['lon'].mean(), zoom=10)
    layer = pdk.Layer("ScatterplotLayer", df_map, get_position='[lon, lat]', get_color='color', get_radius='radius', pickable=True)
    
    st.pydeck_chart(pdk.Deck(map_style=None, initial_view_state=view_state, layers=[layer],
                             tooltip={"text": "{Address}\nPrice: ${Price}\nNet: ${Net $}"}))

    if not df_ranked.empty:
        st.subheader("📊 Comparative Ranking")
        st.dataframe(df_ranked.drop(columns=['lat', 'lon', 'DP', 'Gross', 'OpEx', 'Mtg']), use_container_width=True, hide_index=True,
                     column_config={"Price": st.column_config.NumberColumn(format="$%d"), "Net $": st.column_config.NumberColumn(format="$%d"),
                                    "Cap Rate %": st.column_config.NumberColumn(format="%.2f%%"), "CoC %": st.column_config.ProgressColumn(min_value=0, max_value=15, format="%.2f%%")})

        top = df_ranked.iloc[0]
        st.success(f"🏆 **Top Choice (Ranked by CoC %):** {top['Address']}")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Down Payment Req", f"${top['DP']:,.0f}"); r2.metric("Gross Annual Income", f"${top['Gross']:,.0f}"); r3.metric("Annual Operating Ex", f"${top['OpEx']:,.0f}"); r4.metric("Annual Mortgage", f"${top['Mtg']:,.0f}")

show_disclaimer()
