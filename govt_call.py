import requests

def worldbank_search_indicator(query, max_results=3):
    """
    Search the World Bank indicators for a relevant code based on the query.
    Returns a list of indicator codes and their names.
    """
    url = "http://api.worldbank.org/v2/indicator"
    params = {"format": "json", "per_page": "10000"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        results = []
        for indicator in data[1]:
            searchspace = (indicator['name'] + " " + indicator['id']).lower()
            if query.lower() in searchspace:
                results.append({
                    "id": indicator['id'],
                    "name": indicator['name'],
                    "source": indicator.get('source', {}).get('value', ''),
                })
                if len(results) >= max_results:
                    break
        return results if results else [{"error": f"No matching World Bank indicators for '{query}'."}]
    except Exception as e:
        return [{"error": f"WorldBank: {e}"}]

def fetch_worldbank_indicator(country, indicator, years="2010:2023", limit=3):
    url = f"http://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
    params = {"format": "json", "date": years}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            return {"error": "WorldBank: No data found for this indicator/country/year range."}
        if not isinstance(data[1], list):
            return {"error": f"WorldBank: Unexpected result {data}"}
        vals = [
            {"year": entry['date'], "value": entry['value']}
            for entry in data[1] if entry.get("value") is not None
        ][:limit]
        return {"indicator": indicator, "country": country, "data": vals}
    except Exception as e:
        return {"error": f"WorldBank: {e}"}

def worldbank_query(query, country_code="IN", years="2010:2023", max_results=2):
    """
    Full AI-integrable pipeline:
    - Finds relevant World Bank indicator codes for the query
    - Fetches most recent values for the specified country
    Returns jsonable dict with matching indicators and values.
    """
    result = {"query": query, "country": country_code, "results": []}
    indicators = worldbank_search_indicator(query, max_results=max_results)
    for ind in indicators:
        if "error" in ind:
            result["results"].append(ind)
            continue
        values = fetch_worldbank_indicator(country_code, ind["id"], years=years, limit=max_results)
        entry = {
            "indicator_id": ind["id"],
            "indicator_name": ind["name"],
            "country": country_code,
            "years": years,
            "data": values.get("data") if "data" in values else [],
        }
        if "error" in values:
            entry["error"] = values["error"]
        result["results"].append(entry)
    if not result["results"]:
        result["results"].append({"error": f"No indicators found for query '{query}'."})
    return result

def worldbank_context_string(res):
    """
    Format the world bank result dict as a prompt-friendly summary.
    """
    out = [f"[World Bank Data Search: '{res['query']}' for {res['country']}]"]
    for ind in res["results"]:
        if "error" in ind:
            out.append(f"Error: {ind['error']}")
            continue
        out.append(f"{ind['indicator_name']} (ID: {ind['indicator_id']})")
        if "data" in ind and ind["data"]:
            for x in ind["data"]:
                out.append(f"  Year: {x['year']}  Value: {x['value']}")
        else:
            out.append("  (No data found for this period/country)")
    return "\n".join(out)

# ===== Standalone CLI Entry-point =====
if __name__ == "__main__":
    print("=== World Bank Universal Data Search App ===")
    print("You can try queries like: GDP, life expectancy, population, CO2 emissions, literacy, forest area ...")
    print("-" * 64)
    query = input("Enter World Bank indicator search (e.g. 'GDP', 'population growth', 'CO2'): ").strip()
    country = input("Country code (2-letter, default 'IN'): ").strip().upper() or "IN"
    res = worldbank_query(query, country_code=country)
    print("\n== SUMMARY FOR AI PROMPT ==\n")
    print(worldbank_context_string(res))
    # You can also use 'res' as evidence in your AI pipeline
