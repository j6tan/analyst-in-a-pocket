import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. WEALTHSIMPLE TYPEFACE (Inter) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 2. DYNAMIC LAYOUT (De-Squishing) */
        .block-container {
            padding-top: clamp(2rem, 5vh, 5rem) !important;
            padding-bottom: 5rem !important;
            padding-left: clamp(1rem, 6vw, 10rem) !important;
            padding-right: clamp(1rem, 6vw, 10rem) !important;
            max-width: 1400px !important;
        }

        /* 3. DYNAMIC EDITORIAL TITLES (800 Weight) */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.045em !important; /* Tight letter spacing */
            line-height: 1.05 !important;
            font-size: clamp(2.2rem, 4.8vw, 3.8rem) !important; 
            color: #1a1a1a !important;
            margin-bottom: 1.2rem !important;
        }

        h2 {
            font-size: clamp(1.5rem, 2.8vw, 2.4rem) !important;
            font-weight: 700 !important;
            letter-spacing: -0.025em !important;
        }

        /* 4. 50% GREY PILL BUTTONS */
        div.stButton > button {
            background-color: #7F7F7F !important; /* 50% Grey */
            color: #ffffff !important;
            border: none !important;
            border-radius: 50px !important; /* Pill Shape */
            padding: 0.7rem clamp(1.5rem, 3vw, 3rem) !important;
            font-weight: 600 !important;
            font-size: clamp(0.9rem, 1vw, 1.1rem) !important;
            letter-spacing: -0.01em !important;
            transition: all 0.25s ease-in-out !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }

        div.stButton > button:hover {
            background-color: #666666 !important; /* Slightly darker grey on hover */
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
        }

        /* 5. SECONDARY / BACK BUTTONS */
        div.stButton > button[kind="secondary"] {
            background-color: #EDEDED !important;
            color: #444444 !important;
        }

        /* 6. DYNAMIC CARDS */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border-radius: 24px !important;
            padding: clamp(1.5rem, 4vw, 3rem) !important;
            background-color: #ffffff !important;
            border: 1px solid #f0f0f0 !important;
            box-shadow: 0 12px 40px rgba(0,0,0,0.04) !important;
        }

        /* 7. DYNAMIC METRICS */
        [data-testid="stMetricValue"] {
            font-weight: 800 !important;
            font-size: clamp(1.8rem, 4vw, 2.8rem) !important;
            letter-spacing: -0.04em !important;
        }
        
        /* Hide Default Clutter */
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
