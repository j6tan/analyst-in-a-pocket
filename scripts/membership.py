import streamlit as st
import os
import base64
from style_utils import inject_global_css

# Inject standard styles
inject_global_css()

# --- 1. THEME VARIABLES ---
PRIMARY_GOLD = "#CEB36F"
CHARCOAL = "#2E2B28"
OFF_WHITE = "#F8F9FA"
SLATE_ACCENT = "#4A4E5A"
BORDER_GREY = "#DEE2E6"

# --- 2. INLINE LOGO & HEADER ---
def get_inline_logo(img_name="logo.png", width=75):
    img_path = img_name
    if not os.path.exists(img_path):
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_name)
        
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" style="width: {width}px; flex-shrink: 0;">'
    return "<span style='font-size: 50px;'>🔥</span>"

logo_html = get_inline_logo(width=75)

st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: flex-start; gap: 15px; margin-top: -20px; margin-bottom: 25px;'>
        {logo_html}
        <h1 style='margin: 0 !important; padding: 0 !important; line-height: 1 !important;'>Upgrade to Pro Analyst 💎</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding: 0px 0px 30px 0px;">
    <p style='font-size: 1.1em; color: #4A4E5A; line-height: 1.5;'>
        Unlock the advanced wealth strategies, institutional-grade real estate models, and the ultimate FIRE Toolkit. 
        Choose the plan that fits your investing timeline.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 3. PRICING TIERS (3 Columns) ---
c1, c2, c3 = st.columns(3)

# TIER 1: WEEKEND PASS
with c1:
    st.markdown(f"""
    <div style="background-color: white; padding: 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; height: 380px; display: flex; flex-direction: column;">
        <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.2em;">48-Hour Weekend Pass</h3>
        <h1 style="color: {CHARCOAL}; font-size: 2.5em; margin: 10px 0px;">$4.99<span style="font-size: 0.4em; color: #6c757d;"> one-time</span></h1>
        <p style="color: #6c757d; font-size: 0.9em; flex-grow: 1;">
            Perfect for the casual house hunter who found a property on Saturday and needs to run the development numbers before Monday.
        </p>
        <ul style="color: {SLATE_ACCENT}; font-size: 0.9em; padding-left: 20px; margin-bottom: 25px;">
            <li>Full Access to all Pro Tools</li>
            <li>Export PDF Reports</li>
            <li>Expires in 48 hours</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Get Weekend Pass", key="btn_weekend", use_container_width=True):
        st.info("Stripe Checkout Link will go here!")

# TIER 2: MONTHLY PRO (Highlighted)
with c2:
    st.markdown(f"""
    <div style="background-color: {OFF_WHITE}; padding: 25px; border-radius: 12px; border: 3px solid {PRIMARY_GOLD}; position: relative; height: 380px; display: flex; flex-direction: column; transform: scale(1.03); box-shadow: 0 10px 20px rgba(0,0,0,0.05);">
        <div style="position: absolute; top: -14px; left: 50%; transform: translateX(-50%); background-color: {PRIMARY_GOLD}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold;">RECOMMENDED</div>
        <h3 style="color: {CHARCOAL}; margin-top: 0; font-size: 1.3em;">The Monthly Pro</h3>
        <h1 style="color: {CHARCOAL}; font-size: 2.8em; margin: 10px 0px;">$9.99<span style="font-size: 0.35em; color: #6c757d;"> / mo</span></h1>
        <p style="color: #6c757d; font-size: 0.95em; flex-grow: 1;">
            For the active T4 investor, stock trader, or aggressive house hunter analyzing multiple properties over several months.
        </p>
        <ul style="color: {CHARCOAL}; font-size: 0.95em; padding-left: 20px; margin-bottom: 25px; font-weight: 500;">
            <li>Unlimited Scenario Storage</li>
            <li>Advanced Yield Calculators</li>
            <li>Cancel Anytime</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    # Use primary type for the recommended button
    if st.button("Subscribe to Pro", type="primary", key="btn_monthly", use_container_width=True):
        st.info("Stripe Checkout Link will go here!")

# TIER 3: LIFETIME UNLOCK
with c3:
    st.markdown(f"""
    <div style="background-color: white; padding: 25px; border-radius: 12px; border: 1px solid {BORDER_GREY}; height: 380px; display: flex; flex-direction: column;">
        <h3 style="color: {SLATE_ACCENT}; margin-top: 0; font-size: 1.2em;">Lifetime Unlock</h3>
        <h1 style="color: {CHARCOAL}; font-size: 2.5em; margin: 10px 0px;">$299<span style="font-size: 0.4em; color: #6c757d;"> one-time</span></h1>
        <p style="color: #6c757d; font-size: 0.9em; flex-grow: 1;">
            For the serious "one-and-done" buyer who hates subscriptions and wants a permanent financial tool in their arsenal.
        </p>
        <ul style="color: {SLATE_ACCENT}; font-size: 0.9em; padding-left: 20px; margin-bottom: 25px;">
            <li>Permanent Pro Access</li>
            <li>All Future Updates Included</li>
            <li>No recurring fees ever</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Unlock Lifetime", key="btn_lifetime", use_container_width=True):
        st.info("Stripe Checkout Link will go here!")

st.divider()

st.markdown("""
<div style="text-align: center; color: #6c757d; font-size: 0.9em;">
    🔒 Secure payments processed by Stripe. Prices listed in CAD.
</div>
""", unsafe_allow_html=True)
