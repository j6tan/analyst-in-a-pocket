import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* Wealthsimple-inspired Global Styles */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [data-testid="stapp"] {
            font-family: 'Inter', sans-serif;
            background-color: #FFFFFF;
        }

        /* 1. Universal "De-Squishing" */
        .block-container {
            padding-top: 4rem !important; /* Prevents button cutoff */
            padding-bottom: 5rem;
            padding-left: 6rem !important;
            padding-right: 6rem !important;
            max-width: 1200px; /* Standard readable width for fintech apps */
        }

        /* 2. Wealthsimple Header Style */
        h1 {
            font-weight: 700 !important;
            color: #1a1a1a !important;
            letter-spacing: -0.02em !important;
            margin-bottom: 1.5rem !important;
            white-space: nowrap !important;
        }

        h2, h3 {
            color: #2a2a2a !important;
            font-weight: 600 !important;
        }

        /* 3. Clean Buttons (Wealthsimple Gold/Yellow) */
        div.stButton > button {
            background-color: #FFD448 !important; /* WS Yellow */
            color: #1a1a1a !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }

        div.stButton > button:hover {
            background-color: #f7c325 !important;
            transform: translateY(-1px);
        }

        /* 4. Secondary/Back Buttons */
        div.stButton > button[kind="secondary"] {
            background-color: #f2f2f2 !important;
            color: #4a4a4a !important;
        }

        /* 5. Inputs & Forms */
        [data-testid="stNumberInput"], [data-testid="stTextInput"], [data-testid="stSelectbox"] {
            border-radius: 8px !important;
            margin-bottom: 1rem;
        }

        /* 6. Custom Cards (Passport/Tools) */
        .stElementContainer div[data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
            border: 1px solid #e5e5e5 !important;
            border-radius: 12px !important;
            padding: 2rem !important;
            background-color: #ffffff !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
        }

        /* 7. The Paywall Blur (Option C) */
        .blurred-content {
            filter: blur(10px);
            opacity: 0.6;
            pointer-events: none;
            user-select: none;
        }
        </style>
    """, unsafe_allow_html=True)
