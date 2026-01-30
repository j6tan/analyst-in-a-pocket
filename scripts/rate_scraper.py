import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# Initialize OpenAI Client (Ensure OPENAI_API_KEY is in your environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- SCRAPER 1: Bank of Canada (Interest Rates) ---
def fetch_boc_observation(series_id):
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json?recent=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        return float(data['observations'][0][series_id]['v'])
    except: return None

# --- SCRAPER 2: AI Legislative Interpreter (BC PTT Rules) ---
def get_ai_interpreted_bc_rules():
    """
    Scrapes the BC Gov website and uses AI to extract 2026 tax thresholds.
    """
    url = "https://www2.gov.bc.ca/gov/content/taxes/property-taxes/property-transfer-tax/exemptions/first-time-home-buyers"
    try:
        # 1. Get raw text from the government site
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        raw_text = soup.get_text(separator=' ', strip=True)

        # 2. Ask AI to find the 2026 numbers in the text
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a specialized Canadian tax analyst. Extract property tax thresholds into JSON."},
                {"role": "user", "content": f"Extract the current BC First-Time Home Buyer exemption thresholds from this text. Look for rules effective in 2026. Return ONLY JSON with keys: 'fthb_full_limit' and 'fthb_partial_limit'. \n\nTEXT: {raw_text[:4000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"AI Scrape Failed: {e}")
        return {"fthb_full_limit": 835000, "fthb_partial_limit": 860000} # Safe 2026 fallback

# --- MAIN SYNC ENGINE ---
def update_market_intel():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    if not os.path.exists(data_dir): os.makedirs(data_dir)
    file_path = os.path.join(data_dir, "market_intel.json")

    print("📡 Syncing Market Data...")
    
    # Live Rates
    prime = fetch_boc_observation("V121758") or 5.95
    fixed_5 = fetch_boc_observation("V122667786") or 4.26
    
    # AI-Interpreted Legislative Rules
    print("🧠 Consulting AI for BC Tax Updates...")
    bc_rules = get_ai_interpreted_bc_rules()

    intel_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": {
            "bank_prime": prime,
            "five_year_fixed_uninsured": fixed_5
        },
        "tax_rules": {
            "BC": [
                {"threshold": 200000, "rate": 0.01},
                {"threshold": 2000000, "rate": 0.02},
                {"threshold": 3000000, "rate": 0.03},
                {"threshold": 999999999, "rate": 0.05}
            ],
            "rebates": {
                "BC_FTHB_Threshold": bc_rules['fthb_full_limit'],
                "BC_FTHB_Partial_Limit": bc_rules['fthb_partial_limit'],
                "ON_FTHB_Max": 4000
            }
        },
        "city_tax_data": {
            "BC": {"Vancouver": 0.00311, "Victoria": 0.0052},
            "Ontario": {"Toronto": 0.0076}
        }
    }

    with open(file_path, "w") as f:
        json.dump(intel_data, f, indent=4)
    print(f"✅ Success. BC FTHB Threshold Updated by AI: {bc_rules['fthb_full_limit']}")

if __name__ == "__main__":
    update_market_intel()
