import requests
import json
import os
from datetime import datetime

# ... (fetch_boc_observation and fetch_provincial_yields remain the same) ...

def update_market_intel():
    # ... (directory setup remains the same) ...

    # --- 1. PREPARE CURRENT INTEL WITH 2026 COMPLIANT RULES ---
    intel_data = {
        "last_updated": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "boc_overnight": overnight,
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5
        },
        "provincial_yields": yields,
        "city_tax_data": {
            "Ontario": {
                "Toronto": 0.0076, # Updated for 2.2% 2026 increase
                "Ottawa": 0.01227, "Mississauga": 0.0086, "Brampton": 0.01015,
                "Hamilton": 0.01497, "London": 0.01573, "Markham": 0.0065,
                "Vaughan": 0.00695, "Kitchener": 0.01356, "Windsor": 0.0185,
                "Outside Toronto": 0.0075
            },
            "BC": {
                "Vancouver": 0.00311, # 0% Increase for 2026 confirmed
                "Surrey": 0.0034, "Burnaby": 0.0048, "Richmond": 0.0032,
                "Kelowna": 0.00444, "Victoria": 0.0052, "Other BC": 0.0040
            },
            "Alberta": {
                "Calgary": 0.0063, # Updated for 1.64% 2026 increase
                "Edmonton": 0.00816, "Other Alberta": 0.0065
            }
        },
        "tax_rules": {
            "Ontario": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 999999999, "rate": 0.025}
            ],
            "Toronto_Municipal": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.025},
                {"threshold": 4000000, "rate": 0.044}, # NEW APRIL 2026 TIER
                {"threshold": 5000000, "rate": 0.0545}, # NEW APRIL 2026 TIER
                {"threshold": 999999999, "rate": 0.086} # MAX TIER FOR $20M+
            ],
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05}
            ],
            "rebates": {
                "ON_FTHB_Max": 4000,
                "Toronto_FTHB_Max": 4475,
                "BC_FTHB_Threshold": 835000, # UPDATED FOR 2026
                "BC_FTHB_Partial_Limit": 860000 # UPDATED FOR 2026
            }
        }
    }
    # ... (historical entry and file saving remains the same) ...
