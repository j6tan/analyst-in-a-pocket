import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. Typography & Global Reset */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', -apple-system, sans-serif !important;
            background-color: #FFFFFF !important;
            color: #1a1a1a !important;
        }

        /* 2. Expansive Layout (De-Squishing) */
        .block-container {
            padding-top: 5rem !important; 
            padding-bottom: 5rem !important;
            padding-left: 7% !important;
            padding-right: 7% !important;
            max-width: 1400px !important;
        }

        /* 3. Wealthsimple Ink Headers */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            color: #000000 !important;
            font-size: 3rem !important;
            margin-bottom: 2rem !important;
        }

        h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            color: #1a1a1a !important;
            margin-top: 2rem !important;
        }

        /* 4. The Wealthsimple "Gold" Button */
        div.stButton > button {
            background-color: #FFD448 !important; /* WS Signature Gold */
            color: #000000 !important;
            border: none !important;
            border-radius: 50px !important; /* Pills, not boxes */
            padding: 0.75rem 2.5rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            transition: all 0.3s ease !important;
        }

        div.stButton > button:hover {
            background-color: #f7c325 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        }

        /* 5. Clean White Cards */
        [data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            background-color: #FFFFFF !important;
            border: 1px solid #EDEDED !important;
            border-radius: 16px !important;
            padding: 2.5rem !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.04) !important;
        }

        /* 6. Inputs - Minimalist Borders */
        .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 12px !important;
            border: 1px solid #D1D1D1 !important;
            background-color: #FAFAFA !important;
        }

        /* 7. Hide Streamlit Branding */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
