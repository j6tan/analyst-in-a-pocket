import streamlit as st

def inject_global_css():
    st.markdown("""
        <style>
        /* 1. IMPORT GOOGLE FONTS (Inter is the closest match to Wealthsimple) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');
        
        /* 2. APPLY TO ALL ELEMENTS */
        html, body, [data-testid="stAppViewContainer"], .stMarkdown, p, span {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: #1a1a1a !important;
            -webkit-font-smoothing: antialiased;
        }

        /* 3. WEALTHSIMPLE EDITORIAL TITLES */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.04em !important; /* This "tight" spacing is the WS secret */
            line-height: 1.1 !important;
            font-size: 3.2rem !important;
            color: #000000 !important;
        }

        h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
            color: #1a1a1a !important;
        }

        /* 4. BUTTON TEXT STYLE */
        div.stButton > button {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            text-transform: none !important; /* WS avoids all-caps buttons */
            background-color: #FFD448 !important;
            border-radius: 50px !important;
            border: none !important;
            padding: 0.6rem 2rem !important;
        }

        /* 5. METRIC LABEL STYLE (The small text above numbers) */
        [data-testid="stMetricLabel"] p {
            font-weight: 500 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            font-size: 0.75rem !important;
            color: #666666 !important;
        }

        /* 6. INPUT LABEL STYLE */
        label[data-testid="stWidgetLabel"] p {
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            margin-bottom: 0.5rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
