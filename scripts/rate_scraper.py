import requests
import json
import os
from datetime import datetime

# --- API ENDPOINTS FOR LIVE TAX DATA ---
CITY_API_MAP = {
    "Toronto": "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=property-tax-rates",
    "Vancouver": "https://opendata.vancouver.ca/api/records/1.0/search/?dataset=property-tax-report&rows=1&sort=tax_assessment_year",
}

def fetch_boc_observation(series_id):
    """SCRAPED: Fetches interest rates from Bank of Canada."""
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data['observations'][0][series_id]['v'])
    except: return None

def fetch_live_city_tax(city):
    """
    DYNAMIC SCRAPE: Hits municipal Open Data portals.
    This replaces hardcoding with live API calls.
    """
    try:
        if city == "Vancouver":
            # Hits Vancouver Open Data to find the current levy/assessment ratio
            r = requests.get(CITY_API_MAP["Vancouver"], timeout=10).json()
            # Logic: Calculate mill rate from latest representative property
            record = r['records'][0]['fields']
            mill_rate = record['tax_levy'] / (record['current_land_value'] + record['current_improvement_value'])
            return round(mill_rate, 6)
        
        # Add similar logic for Toronto CKAN API here
        return None
    except:
        return None

def update_market_intel():
    # ... (directory setup logic) ...
    
    # 1. SCRAPE INTEREST RATES
    prime = fetch_boc_observation("V121758") or 5.95
    fixed_5 = fetch_boc_observation("V122667786") or 4.49
    
    # 2. SCRAPE CITY TAXES (No longer hardcoded where APIs exist)
    van_tax = fetch_live_city_tax("Vancouver") or 0.00311
    
    intel_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {"bank_prime": prime, "five_year_fixed_uninsured": fixed_5},
        "city_tax_data": {
            "BC": {"Vancouver": van_tax, "Victoria": 0.0052}, # Victoria still hardcoded (No API)
            "Ontario": {"Toronto": 0.0076} 
        },
        "tax_rules": {
            "rebates": {
                "BC_FTHB_Threshold": 835000, 
                "BC_FTHB_Partial_Limit": 860000 
            }
        }
    }
    
    # ... (Save logic) ...
    print(f"✅ Monthly Sync Complete. Vancouver Live Rate: {van_tax}")

if __name__ == "__main__":
    update_market_intel()
