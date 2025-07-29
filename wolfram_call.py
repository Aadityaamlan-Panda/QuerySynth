import requests

import json
import os

# Load API keys from config.json
def load_config(config_path='config.json'):
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
# Usage: config['news_api_key'], config['pexels_api_key'], etc.

WOLFRAM_APP_ID = config['wolfram_app_id']  # Your Wolfram Alpha App ID

def query_wolfram(query, app_id=WOLFRAM_APP_ID, timeout=12):
    """
    Query Wolfram Alpha for a given input, return structured pod results for AI/RAG.
    Returns a list of dicts: [{'title': ..., 'text': ...}, ...]
    Handles API/network errors gracefully.
    """
    url = "http://api.wolframalpha.com/v2/query"
    params = {
        "input": query,
        "appid": app_id,
        "output": "JSON"
    }
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        data = resp.json()
    except Exception as e:
        return [{"title": "WolframAlpha Error", "text": str(e)}]

    # Check for immediate query errors (e.g., no pods, computation failed, bad input)
    qres = data.get('queryresult', {})
    if not qres.get("success", False):
        error_msg = qres.get('error', {}).get('msg', "WolframAlpha query did not succeed.")
        return [{"title": "WolframAlpha Error", "text": error_msg or "No results."}]

    pods = qres.get('pods', [])
    results = []
    for pod in pods:
        subpods = pod.get('subpods', [])
        pod_title = pod.get('title', '')
        for sub in subpods:
            text = sub.get('plaintext')
            if text and text.strip():
                results.append({
                    "title": pod_title,
                    "text": text.strip()
                })
    if not results:
        # Sometimes WA returns only images—flag as such
        return [{"title": "WolframAlpha", "text": "[No plaintext result, check source for plot/data image]"}]
    return results

def wolfram_results_to_prompt(results, context_max=1500):
    """
    Format WA pod results for prompt injection, with truncation.
    """
    blocks = []
    char_count = 0
    for idx, pod in enumerate(results):
        block = f"[WolframAlpha Pod {idx+1}] {pod['title']}\n{pod['text']}\n"
        if char_count + len(block) > context_max:
            break
        blocks.append(block)
        char_count += len(block)
    return "\n".join(blocks)

# ------------------ Example usage ------------------
if __name__ == "__main__":
    query = input("WolframAlpha query: ")
    results = query_wolfram(query)
    import json
    # 1. As raw JSON for code/AI use:
    print(json.dumps(results, ensure_ascii=False, indent=2))
    # 2. As prompt snippet:
    print("\n==== FOR AI PROMPT ====\n")
    print(wolfram_results_to_prompt(results, context_max=1200))
