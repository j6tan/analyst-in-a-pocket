import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk 
import requests 
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

# --- 2. BRANDING COLORS ---
PRIMARY_GOLD_RGBA = [206, 179, 111, 255] 
CHARCOAL_RGBA = [46, 43, 40, 255]       
DARK_RED = "#8B0000"
SUCCESS_GREEN = "#28a745"

st.title("Pro Rental Portfolio Analyzer")

# --- 3. GLOBAL SETTINGS (FIXED PERSISTENCE) ---
# Added explicit keys to all global inputs so they never reset on reload
with st.container(border=True):
    st.subheader("⚙️ Global Settings")
    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1.5, 1, 1])
    with g_col1:
        dp_mode = st.radio("Down Payment Mode", ["Percentage (%)", "Fixed Amount ($)"], horizontal=True, key="g_dp_mode")
    with g_col2:
        dp_global_val = st.number_input(f"Down Payment ({'%' if 'Percent' in dp_mode else '$'})", 
                                        value=20.0 if "Percent" in dp_mode else 100000.0, key="g_dp_val")
    with g_col3:
        m_rate = st.number_input("Mortgage Interest Rate (%)", value=5.1, step=0.1, key="g_m_rate")
    with g_col4:
        m_amort = st.number_input("Amortization (Years)", value=25, step=1, key="g_m_amort")
    
    g_col5, g_col6 = st.columns([2, 1])
    with g_col5:
        use_mgmt = st.checkbox("Will you use a Property Manager?", key="g_use_mgmt")
    with g_col6:
        mgmt_fee = st.number_input("Property Management Fee (%)", value=8.0, step=0.5, key="g_mgmt_fee") if use_mgmt else 0.0

# --- 4. LISTING MANAGEMENT ---
if 'rental_listings' not in st.session_state:
    st.session_state.rental_listings = [
        {"address": "3399 Noel Drive, Burnaby, BC", "lat": 49.2667, "lon": -122.9000, "price": 800000, "tax": 3000, "strata": 400, "rent": 3500, "beds": 2, "baths": 2, "year": 2010, "ins": 100, "sqft": 850},
    ]

def sync_listing(index, field, key):
    st.session_state.rental_listings[index][field] = st.session_state[key]

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
                st.rerun()
        except: pass

st.subheader("🏠 Property Underwriting")
for i, listing in enumerate(st.session_state.rental_listings):
    with st.expander(f"Listing #{i+1}: {listing['address'][:30]}...", expanded=(i==len(st.session_state.rental_listings)-1)):
        r1_c1, r1_c2, r1_c3 = st.columns([1.6, 1, 1])
        with r1_c1: 
            st.text_input("Address", value=listing['address'], key=f"addr_{i}", label_visibility="collapsed", on_change=sync_listing, args=(i, 'address', f"addr_{i}"))
        with r1_c2: 
            st.button("📍 Add to Map", key=f"geo_{i}", on_click=geocode_address, args=(i,), use_container_width=True)
        with r1_c3: 
            if st.button("🗑️ Remove", key=f"del_{i}", use_container_width=True):
                st.session_state.rental_listings.pop(i); st.rerun()

        r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns([2.6, 0.6, 0.6, 1, 1])
        with r2_c1: 
            st.number_input("Listing Price ($)", value=listing['price'], key=f"pr_{i}", on_change=sync_listing, args=(i, 'price', f"pr_{i}"))
        with r2_c2: 
            st.number_input("Beds", value=listing.get('beds', 1), key=f"bd_{i}", on_change=sync_listing, args=(i, 'beds', f"bd_{i}"))
        with r2_c3: 
            st.number_input("Baths", value=listing.get('baths', 1), key=f"ba_{i}", on_change=sync_listing, args=(i, 'baths', f"ba_{i}"))
        with r2_c4: 
            st.number_input("Sqft", value=listing.get('sqft', 0), key=f"sq_{i}", on_change=sync_listing, args=(i, 'sqft', f"sq_{i}"))
        with r2_c5: 
            st.number_input("Year Built", value=listing.get('year', 2000), key=f"yr_{i}", on_change=sync_listing, args=(i, 'year', f"yr_{i}"))

        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: 
            st.number_input("Monthly Rent ($)", value=listing['rent'], key=f"rt_{i}", on_change=sync_listing, args=(i, 'rent', f"rt_{i}"))
        with r3_c2: 
            st.number_input("Property Tax ($)", value=listing['tax'], key=f"tx_{i}", on_change=sync_listing, args=(i, 'tax', f"tx_{i}"))
        with r3_c3: 
            st.number_input("Strata Fees ($)", value=listing['strata'], key=f"st_{i}", on_change=sync_listing, args=(i, 'strata', f"st_{i}"))
        with r3_c4: 
            st.number_input("Monthly Insurance ($)", value=listing.get('ins', 100), key=f"in_{i}", on_change=sync_listing, args=(i, 'ins', f"in_{i}"))

# FIXED: 'ins', 'beds', 'baths', 'sqft', and 'year' are now injected into the blank template
if len(st.session_state.rental_listings) < 10:
    st.button("➕ Add Another Listing", on_click=lambda: st.session_state.rental_listings.append({
        "address": "", "lat": 0.0, "lon": 0.0, "price": 0, "tax": 0, "strata": 0, "rent": 0, 
        "beds": 1, "baths": 1, "sqft": 0, "year": 2000, "ins": 100
    }))

# --- 5. CALCULATIONS ENGINE ---
full_analysis_list = []
for idx, l in enumerate(st.session_state.rental_listings):
    if l.get('lat') and l.get('lon'):
        noi, dp_amt, ann_mtg, net_cf, coc_ret, psf = 0, 0, 0, 0, 0, 0
        gross_inc = l['rent'] * 12
        mgmt_cost = (l['rent'] * 12 * (mgmt_fee / 100))
        reserves = (l['rent'] * 12 * 0.05) 
        
        # This is where the KeyError happened! With the 'ins' key added to the blank template above, this is now safe.
        op_ex = l['tax'] + (l['strata'] * 12) + (l.get('ins', 100) * 12) + mgmt_cost + reserves
        
        if l['price'] > 0:
            noi = gross_inc - op_ex
            dp_amt = (l['price'] * (dp_global_val / 100)) if "Percent" in dp_mode else dp_global_val
            loan = l['price'] - dp_amt
            r = (m_rate / 100) / 12
            pmt = loan * (r * (1 + r)**(m_amort*12)) / ((1 + r)**(m_amort*12) - 1) if r > 0 else loan / (m_amort*12)
            ann_mtg = pmt * 12
            net_cf = noi - ann_mtg
            coc_ret = (net_cf / dp_amt) * 100 if dp_amt > 0 else 0
            psf = l['price'] / l['sqft'] if l.get('sqft', 0) > 0 else 0

        full_analysis_list.append({
            "Address": l['address'], "Price": l['price'], "Area (sqft)": l.get('sqft', 0),
            "PSF": psf, "Gross Annual Rent": gross_inc, "Annual OpEx": op_ex,
            "Annual Mortg": ann_mtg, "Annual Net Cash Flow": net_cf,
            "Cap Rate %": (noi / l['price']) * 100 if l['price']>0 else 0,
            "CoC %": coc_ret, "DP_RAW": dp_amt, "lat": l['lat'], "lon": l['lon']
        })

# --- 6. POI MAP LAYER MATIC (WITH REAL ICONS) ---
@st.cache_data(ttl=86400) 
def fetch_osm_pois(lat, lon, radius, poi_type):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query_map = {
        "Schools": 'nwr["amenity"="school"]',
        "Hospitals": 'nwr["amenity"="hospital"]',
        "Bus Stops": 'node["highway"="bus_stop"]',
        "Parks": 'nwr["leisure"="park"]'
    }
    icon_map = {"Schools": "🏫", "Hospitals": "🏥", "Bus Stops": "🚌", "Parks": "🌲"}
    
    if poi_type not in query_map: return pd.DataFrame()
    
    overpass_query = f"""
    [out:json];
    ({query_map[poi_type]}(around:{radius},{lat},{lon}););
    out center;
    """
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        pois = []
        for element in data['elements']:
            p_lat = element.get('lat', element.get('center', {}).get('lat'))
            p_lon = element.get('lon', element.get('center', {}).get('lon'))
            p_name = element.get('tags', {}).get('name', poi_type[:-1])
            if p_lat and p_lon:
                pois.append({'lat': p_lat, 'lon': p_lon, 'HoverText': f"{poi_type[:-1]}: {p_name}", 'icon': icon_map[poi_type]})
        return pd.DataFrame(pois)
    except:
        return pd.DataFrame()

# --- 7. VISUALS & RANKING ---
if full_analysis_list:
    df_results = pd.DataFrame(full_analysis_list)
    df_ranked = df_results[df_results['Price'] > 0].sort_values(by="CoC %", ascending=False).reset_index(drop=True)
    
    st.divider()
    st.subheader("🗺️ Geographic Portfolio Distribution")
    
    # Layer Controls
    layer_col1, layer_col2, layer_col3, layer_col4, layer_col5 = st.columns(5)
    with layer_col1: show_schools = st.checkbox("🏫 Schools")
    with layer_col2: show_hospitals = st.checkbox("🏥 Hospitals")
    with layer_col3: show_transit = st.checkbox("🚌 Bus Stops")
    with layer_col4: show_parks = st.checkbox("🌲 Parks")
    with layer_col5:
        st.markdown(f'<div style="display: flex; gap: 10px; font-size: 0.8em; justify-content: flex-end; margin-top: 5px;"><span style="color: #CEB36F;">●</span> Top Pick <span style="color: #2E2B28;">●</span> Others</div>', unsafe_allow_html=True)

    # Base Property Pins
    best_addr = df_ranked.iloc[0]['Address'] if not df_ranked.empty else ""
    df_results['Rank'] = df_results['Address'].map(lambda x: df_ranked[df_ranked['Address'] == x].index[0] + 1 if x in df_ranked['Address'].values else "-")
    df_results['Rank_str'] = df_results['Rank'].astype(str) 
    df_results['color'] = df_results['Address'].map(lambda x: PRIMARY_GOLD_RGBA if x == best_addr and x != "" else CHARCOAL_RGBA)
    df_results['HoverText'] = df_results.apply(lambda row: f"Rank #{row['Rank']}: {row['Address']} (${row['Price']:,.0f})", axis=1)

    center_lat, center_lon = df_results['lat'].mean(), df_results['lon'].mean()
    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12)
    
    map_layers = []

    # Properties: Colored Circles
    map_layers.append(pdk.Layer("ScatterplotLayer", df_results, get_position='[lon, lat]', get_color='color', get_radius=180, pickable=True))
    # Properties: Centered White Rank Numbers
    map_layers.append(pdk.Layer("TextLayer", df_results, get_position='[lon, lat]', get_text="Rank_str", get_size=18, get_color=[255, 255, 255, 255], get_alignment_baseline="'center'", get_text_anchor="'middle'"))

    # Dynamic POI Layers (Now using Emoji TextLayers instead of colored dots!)
    if show_schools:
        df_sch = fetch_osm_pois(center_lat, center_lon, 3000, "Schools")
        if not df_sch.empty: map_layers.append(pdk.Layer("TextLayer", df_sch, get_position='[lon, lat]', get_text='icon', get_size=25, pickable=True))
    if show_hospitals:
        df_hos = fetch_osm_pois(center_lat, center_lon, 5000, "Hospitals")
        if not df_hos.empty: map_layers.append(pdk.Layer("TextLayer", df_hos, get_position='[lon, lat]', get_text='icon', get_size=28, pickable=True))
    if show_transit:
        df_bus = fetch_osm_pois(center_lat, center_lon, 1500, "Bus Stops")
        if not df_bus.empty: map_layers.append(pdk.Layer("TextLayer", df_bus, get_position='[lon, lat]', get_text='icon', get_size=20, pickable=True))
    if show_parks:
        df_prk = fetch_osm_pois(center_lat, center_lon, 2000, "Parks")
        if not df_prk.empty: map_layers.append(pdk.Layer("TextLayer", df_prk, get_position='[lon, lat]', get_text='icon', get_size=25, pickable=True))

    st.pydeck_chart(pdk.Deck(
        map_style=None, initial_view_state=view_state, 
        layers=map_layers,
        tooltip={"text": "{HoverText}"} 
    ))

    # --- RANKING TABLE ---
    if not df_ranked.empty:
        st.subheader("📊 Comparative Ranking")
        display_df = df_ranked.drop(columns=['lat', 'lon', 'DP_RAW', 'color', 'Rank', 'Rank_str', 'HoverText'], errors='ignore')
        
        st.dataframe(
            display_df, use_container_width=True, hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn(format="$%d"),
                "Area (sqft)": st.column_config.NumberColumn(format="%d"),
                "PSF": st.column_config.NumberColumn(format="$%d"),
                "Gross Annual Rent": st.column_config.NumberColumn(format="$%d"),
                "Annual OpEx": st.column_config.NumberColumn(format="$%d"),
                "Annual Mortg": st.column_config.NumberColumn(format="$%d"),
                "Annual Net Cash Flow": st.column_config.NumberColumn(format="$%d"),
                "Cap Rate %": st.column_config.NumberColumn(format="%.2f%%"),
                "CoC %": st.column_config.NumberColumn(format="%.2f%%")
            }
        )

        st.subheader("💰 Deep Underwriting (Top Selection)")
        top = df_ranked.iloc[0]
        st.markdown(f"**Selected Listing:** {top['Address']}")

        def styled_metric(label, value, color, is_outflow=True):
            prefix = "-" if is_outflow else ""
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                <p style="margin:0; font-size: 0.85rem; color: #6c757d;">{label}</p>
                <p style="margin:0; font-size: 1.5rem; font-weight: bold; color: {color};">{prefix}${value:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1: styled_metric("Down Payment Req", top['DP_RAW'], DARK_RED)
        with m2: styled_metric("Gross Annual Income", top['Gross Annual Rent'], SUCCESS_GREEN, is_outflow=False)
        with m3: styled_metric("Annual Operating Ex", top['Annual OpEx'], DARK_RED)
        with m4: styled_metric("Annual Mortgage", top['Annual Mortg'], DARK_RED)

show_disclaimer()
