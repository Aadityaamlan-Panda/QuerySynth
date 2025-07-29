import requests
from bs4 import BeautifulSoup

import json
import os

# Load API keys from config.json
def load_config(config_path='config.json'):
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
# Usage: config['news_api_key'], config['pexels_api_key'], etc.

WEATHERAPI_KEY = config['weather_api_key']  # Your key

def fetch_weather(location="Kanpur"):
    """Fetch current weather by city or coordinates. Returns dict with details and meta."""
    url = f"https://api.weatherapi.com/v1/current.json?key={WEATHERAPI_KEY}&q={location}&aqi=yes"
    try:
        resp = requests.get(url, timeout=8)
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "result": None}
    if "error" in data:
        return {"error": data["error"]["message"], "result": None}
    # Optional: Scrape full forecast text from WeatherAPI's free web frontend
    city_url = f"https://www.weatherapi.com/weather/q/{location.replace(' ', '%20')}"
    try:
        page = requests.get(city_url, timeout=10, headers={'User-Agent':'Mozilla/5.0'})
        soup = BeautifulSoup(page.text, "html.parser")
        # Try to fetch full forecast / summary block text if present
        desc = soup.find("div", class_="forecastdesc") or soup.find("div", class_="cond")
        full_text = desc.get_text(strip=True) if desc else ""
    except Exception:
        full_text = ""
    result = {
        "location": data.get("location", {}).get("name", location),
        "region": data.get("location", {}).get("region", ""),
        "country": data.get("location", {}).get("country", ""),
        "localtime": data.get("location", {}).get("localtime", ""),
        "condition": data.get("current", {}).get("condition", {}).get("text", ""),
        "temp_C": data.get("current", {}).get("temp_c", None),
        "temp_F": data.get("current", {}).get("temp_f", None),
        "humidity": data.get("current", {}).get("humidity", None),
        "wind_kph": data.get("current", {}).get("wind_kph", None),
        "aqi": data.get("current", {}).get("air_quality", {}),
        "icon_url": data.get("current", {}).get("condition", {}).get("icon", ""),
        "full_report_text": full_text
    }
    return result

# Example usage:
if __name__ == "__main__":
    import json
    weather = fetch_weather("Kanpur")
    print(json.dumps(weather, ensure_ascii=False, indent=2))
