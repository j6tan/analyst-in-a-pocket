import streamlit as st
import streamlit.components.v1 as components

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

        /* 4. BUTTONS - AGGRESSIVE TARGETING */
        
        /* The Native Streamlit Button Box */
        button[data-testid="baseButton-secondary"] {
            background-color: #EDEDED !important;
            border: 0px solid transparent !important; /* Force kill the faint border */
            border-radius: 50px !important;
            box-shadow: none !important;
            min-height: 42px !important;
            height: 42px !important; /* Lock the height */
            padding: 0 2rem !important;
        }
        
        /* The Text Inside the Native Button */
        button[data-testid="baseButton-secondary"] p {
            color: #444444 !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Hover Effect */
        button[data-testid="baseButton-secondary"]:hover {
            background-color: #D6D6D6 !important;
            color: #444444 !important;
            border: 0px solid transparent !important;
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

        /* 6. PRINT STYLES FOR PDF EXPORT */
        @media print {
            /* Hide the Streamlit Header and Sidebar */
            header[data-testid="stHeader"] {
                display: none !important;
            }
            [data-testid="stSidebar"] {
                display: none !important;
            }
            /* Force background to white for clean printing */
            .stApp {
                background-color: white !important;
            }
            /* Hide specific UI elements you don't want in the report */
            .stButton > button {
                display: none !important;
            }
            /* Expand the main container to use the full page width */
            .main .block-container {
                max-width: 100% !important;
                padding-top: 0 !important;
            }
        }
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

def show_disclaimer():
    st.markdown("---")
    st.markdown("""
    <div style='background-color: #f8f9fa; padding: 16px 20px; border-radius: 5px; border: 1px solid #dee2e6;'>
        <p style='font-size: 12px; color: #6c757d; line-height: 1.6; margin-bottom: 0;'>
            <strong>⚠️ Errors and Omissions Disclaimer:</strong><br>
            This tool is for <strong>informational and educational purposes only</strong>. Figures are based on mathematical estimates and historical data. 
            This does not constitute financial, legal, or tax advice. Consult with a professional before making significant financial decisions.
        </p>
    </div>
    """, unsafe_allow_html=True)

def add_pdf_button():
    """Injects a button that triggers the browser's native Print/Save as PDF dialog."""
    components.html(
        """
        <script>
        function triggerPrint() {
            window.parent.print();
        }
        </script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            body { margin: 0; padding: 0; background: transparent; }
            
            .pdf-btn {
                box-sizing: border-box; /* Stops invisible padding */
                background-color: #EDEDED;
                color: #444444;
                border: none;
                height: 42px; /* Locked to 42px */
                border-radius: 50px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                width: 100%;
                font-family: 'Inter', sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
                white-space: nowrap;
                transition: background-color 0.2s ease-in-out;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                margin: 0;
            }
            .pdf-btn:hover {
                background-color: #D6D6D6;
            }
        </style>
        <button class="pdf-btn" onclick="triggerPrint()">📥 Save to PDF</button>
        """,
        height=42
    )
