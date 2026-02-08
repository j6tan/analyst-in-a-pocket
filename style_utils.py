import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. WEALTHSIMPLE TYPEFACE */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. LAYOUT */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 5rem !important;
            max-width: 1400px !important;
        }

        /* 3. HEADERS */
        h1 { font-weight: 800 !important; letter-spacing: -0.04em !important; font-size: 3rem !important; }
        h2, h3 { font-weight: 700 !important; }

        /* 4. BUTTONS */
        div.stButton > button {
            background-color: #4D4D4D !important;
            color: white !important;
            border-radius: 50px !important;
            padding: 0.6rem 2rem !important;
            border: none !important;
        }
        div.stButton > button:hover { background-color: #333 !important; }
        div.stButton > button[kind="secondary"] {
            background-color: #EDEDED !important;
            color: #444 !important;
        }

        /* 5. SIDEBAR FIXES */
        [data-testid="stSidebarNavItems"] { padding-top: 1rem !important; }
        
        [data-testid="stSidebarNavItems"] > div > :first-child {
            color: #333 !important;
            font-size: 0.75rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            margin-top: 1.5rem !important;
        }
        
        /* FIX: Only hide Footer. Do NOT hide Header (it kills the sidebar toggle) */
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

def check_premium_access():
    """
    Stops execution if the user is not a Pro member.
    """
    if st.session_state.get("is_pro", False):
        return  # Allowed

    # Paywall UI
    st.markdown("""
    <div style="background-color: #F8F9FA; border: 1px solid #ddd; padding: 40px; border-radius: 15px; text-align: center; margin-top: 50px;">
        <div style="font-size: 60px;">🔒</div>
        <h2 style="color: #333; margin-top: 10px;">Pro Feature Locked</h2>
        <p style="color: #666; font-size: 1.1em; max-width: 600px; margin: 0 auto 20px auto;">
            This strategy is an advanced wealth-building tool available exclusively to our Premium subscribers.
        </p>
        <div style="background-color: #FFF8E1; padding: 15px; border-radius: 8px; display: inline-block; margin-bottom: 20px;">
            <span style="color: #CEB36F; font-weight: bold;">✨ Premium Features:</span>
            <ul style="text-align: left; color: #555; margin-bottom: 0;">
                <li>Unlimited Scenario Modeling</li>
                <li>PDF Export & Client Reports</li>
                <li>Advanced Tax & Cash Flow Analysis</li>
            </ul>
        </div>
        <br>
    </div>
    """, unsafe_allow_html=True)
    
    # Upgrade Button
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Upgrade to Pro (Demo)", type="primary", use_container_width=True):
            st.session_state.is_pro = True
            st.rerun()
    
    st.stop()
