import requests
from bs4 import BeautifulSoup
import time

import json
import os

# Load API keys from config.json
def load_config(config_path='config.json'):
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
# Usage: config['news_api_key'], config['pexels_api_key'], etc.


# ==== Place your API keys here ====
NEWSAPI_KEY = config['news_api_key']
GUARDIAN_API_KEY = config['guardian_api_key']
GNEWS_API_KEY = config['gnews_api_key']
NYT_API_KEY = "apikey"  # Replace with your NYT key

def extract_full_news_text(url, timeout=10):
    """Try to extract long text from the article webpage."""
    try:
        resp = requests.get(url, timeout=timeout, headers={'User-Agent':'Mozilla/5.0'})
        soup = BeautifulSoup(resp.content, "html.parser")
        main = soup.find("article")
        if not main:
            main = soup.find("div", {'class': lambda x: x and 'content' in x})
        if not main:
            main = soup
        ptags = main.find_all("p")
        if not ptags:
            ptags = soup.find_all("p")
        text_blobs = [p.get_text(strip=True) for p in ptags if len(p.get_text(strip=True)) > 40]
        return "\n\n".join(text_blobs)[:6000]
    except Exception as e:
        return f"[Could not extract full article: {e}]"

def fetch_newsapi(query, num_articles=3, lang='en'):
    url = (
        'https://newsapi.org/v2/everything?'
        f'q={requests.utils.quote(query)}&'
        f'language={lang}&'
        'sortBy=publishedAt&'
        f'pageSize={num_articles}&'
        f'apiKey={NEWSAPI_KEY}'
    )
    res = []
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if resp.status_code != 200 or "articles" not in data:
            return [{"source": "NewsAPI", "error": data.get('message', f"HTTP {resp.status_code}")}]
    except Exception as e:
        return [{"source": "NewsAPI", "error": f"Request error: {e}"}]
    for article in data.get("articles", []):
        link = article['url']
        full_text = extract_full_news_text(link)
        res.append({
            "source": "NewsAPI",
            "title": article.get("title"),
            "description": article.get("description"),
            "url": link,
            "origin": article.get("source", {}).get("name"),
            "full_text": full_text
        })
        time.sleep(0.5)
    if not res:
        res.append({"source": "NewsAPI", "error": "No articles found for this query."})
    return res

def fetch_guardian(query, num_articles=3):
    if not GUARDIAN_API_KEY or GUARDIAN_API_KEY == "your_guardian_api_key":
        return [{"source": "Guardian", "error": "API key missing"}]
    url = (
        f'https://content.guardianapis.com/search?q={requests.utils.quote(query)}'
        f'&api-key={GUARDIAN_API_KEY}&page-size={num_articles}&show-fields=all'
    )
    res = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return [{"source": "Guardian", "error": f"HTTP {resp.status_code}: {resp.text[:140]}"}]
        data = resp.json()
    except Exception as e:
        return [{"source": "Guardian", "error": f"Request error: {e}"}]
    articles = data.get("response", {}).get("results", [])
    for article in articles:
        web_url = article.get("webUrl")
        full_text = extract_full_news_text(web_url)
        res.append({
            "source": "Guardian",
            "title": article.get("webTitle"),
            "section": article.get("sectionName"),
            "url": web_url,
            "full_text": full_text
        })
        time.sleep(0.5)
    if not res:
        res.append({"source": "Guardian", "error": "No articles found for this query."})
    return res

def fetch_gnews(query, num_articles=3, lang='en'):
    if not GNEWS_API_KEY or GNEWS_API_KEY == "your_gnews_api_key":
        return [{"source": "GNews", "error": "API key missing"}]
    url = (
        f'https://gnews.io/api/v4/search?q={requests.utils.quote(query)}'
        f'&token={GNEWS_API_KEY}&max={num_articles}&lang={lang}&sortby=publishedAt'
    )
    res = []
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "errors" in data or "code" in data:
            return [{"source": "GNews", "error": str(data)}]
    except Exception as e:
        return [{"source": "GNews", "error": f"Request error: {e}"}]
    for article in data.get("articles", []):
        link = article.get("url")
        full_text = extract_full_news_text(link)
        res.append({
            "source": "GNews",
            "title": article.get("title"),
            "description": article.get("description"),
            "url": link,
            "origin": article.get("source", {}).get("name"),
            "full_text": full_text
        })
        time.sleep(0.5)
    if not res:
        res.append({"source": "GNews", "error": "No articles found for this query."})
    return res

def fetch_nyt(query, num_articles=3):
    if not NYT_API_KEY or NYT_API_KEY == "apikey":
        return [{"source": "NYT", "error": "API key missing"}]
    url = (
        f'https://api.nytimes.com/svc/search/v2/articlesearch.json?q={requests.utils.quote(query)}'
        f'&api-key={NYT_API_KEY}&sort=newest&page=0'
    )
    res = []
    try:
        resp = requests.get(url, timeout=12)
        data = resp.json()
        if resp.status_code != 200 or "response" not in data:
            return [{"source": "NYT", "error": data.get('fault', data.get('message', f"HTTP {resp.status_code}"))}]
        docs = data.get("response", {}).get("docs", [])
    except Exception as e:
        return [{"source": "NYT", "error": f"Request error: {e}"}]
    for doc in docs[:num_articles]:
        link = doc.get("web_url")
        full_text = extract_full_news_text(link)
        res.append({
            "source": "NYT",
            "title": doc.get("headline", {}).get("main"),
            "section": doc.get("section_name"),
            "url": link,
            "snippet": doc.get("snippet"),
            "full_text": full_text
        })
        time.sleep(0.5)
    if not res:
        res.append({"source": "NYT", "error": "No articles found for this query."})
    return res

def fetch_all_news(query, num_articles=3):
    """Returns a unified list from all sources, with error diagnostics."""
    combined = []
    for f in [fetch_newsapi, fetch_guardian, fetch_gnews, fetch_nyt]:
        try:
            subresults = f(query, num_articles)
            combined += subresults
            print(f"[DEBUG] {f.__name__} {len(subresults)} results, first: {subresults[0]['title'] if subresults and 'title' in subresults[0] else subresults[0].get('error') if subresults else 'no result'}")
        except Exception as e:
            combined.append({"source": str(f.__name__), "error": str(e)})
    return combined

# Example use - command line or bot call
if __name__ == "__main__":
    import sys, json
    qry = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Enter news search: ")
    results = fetch_all_news(qry, num_articles=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))
