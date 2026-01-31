import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# Initialize OpenAI Client (Ensure OPENAI_API_KEY is in your environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 1. MARKET DATA SCRAPER (Bank of Canada) ---
def fetch_boc_observation(series_id):
    """Programmatic access to BoC macro data (Prime, Overnight, 5yr Fixed)."""
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'observations' in data and len(data['observations']) > 0:
            val = data['observations'][0].get(series_id, {}).get('v')
            return float(val) if val else None
        return None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch {series_id}. Error: {e}")
        return None

# --- 2. AI LEGISLATIVE INTERPRETER (BC PTT Rules) ---
def get_ai_interpreted_bc_rules():
    """Scrapes BC Gov text and uses AI to extract 2026 thresholds ($835k/$860k)."""
    url = "https://www2.gov.bc.ca/gov/content/taxes/property-taxes/property-transfer-tax/exemptions/first-time-home-buyers"
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()[:4000]  # Grab the relevant top section

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Extract the 'full exemption' and 'partial exemption' price thresholds for the BC First Time Home Buyers program as of 2026. Return JSON only: {'fthb_full_limit': int, 'fthb_partial_limit': int}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"fthb_full_limit": 835000, "fthb_partial_limit": 860000}

# --- 3. EXECUTE & UPDATE ---
def update_market_intel():
    # Fetch Rates
    prime = fetch_boc_observation("V39079") or 5.95
    overnight = fetch_boc_observation("V39079") or 2.25
    fixed_5 = fetch_boc_observation("V122667786") or 4.26
    
    # AI Scrape BC Rules
    print("🧠 Consulting AI for BC Legislative Updates...")
    bc_rules = get_ai_interpreted_bc_rules()

    intel_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5,
            "boc_overnight": overnight
        },
        "tax_rules": {
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05}
            ],
            "Ontario": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 999999999, "rate": 0.025}
            ],
            # TORONTO MUNICIPAL RULES (MLTT) - 2026 LUXURY READY
            "Toronto_Municipal": [
                {"threshold": 55000, "rate": 0.005},
                {"threshold": 250000, "rate": 0.01},
                {"threshold": 400000, "rate": 0.015},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.025},
                {"threshold": 4000000, "rate": 0.044},   # April 2026 Luxury Tier
                {"threshold": 5000000, "rate": 0.0545},  # April 2026 Luxury Tier
                {"threshold": 10000000, "rate": 0.065},  # April 2026 Luxury Tier
                {"threshold": 20000000, "rate": 0.0755}, # April 2026 Luxury Tier
                {"threshold": 999999999, "rate": 0.086}  # April 2026 Luxury Tier
            ],
            "rebates": {
                "BC_FTHB_Threshold": bc_rules['fthb_full_limit'],
                "BC_FTHB_Partial_Limit": bc_rules['fthb_partial_limit'],
                "ON_FTHB_Max": 4000,
                "Toronto_FTHB_Max": 4475
            }
        },
        "city_tax_data": {
            "BC": {"Vancouver": 0.00311, "Victoria": 0.0052},
            "Ontario": {"Toronto": 0.0076}
        }
    }

    os.makedirs("data", exist_ok=True)
    with open("data/market_intel.json", "w") as f:
        json.dump(intel_data, f, indent=4)
    print("✅ Market Intel Updated with Toronto Municipal rules.")

if __name__ == "__main__":
    update_market_intel()
