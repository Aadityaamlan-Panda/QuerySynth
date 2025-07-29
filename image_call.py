import requests
import os

# For CLI image preview in Jupyter/IPython only
try:
    from PIL import Image
    from io import BytesIO
    from IPython.display import display
except ImportError:
    Image = display = None

import json
import os

# Load API keys from config.json
def load_config(config_path='config.json'):
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config()
# Usage: config['news_api_key'], config['pexels_api_key'], etc.


PEXELS_API_KEY = config['pexels_api_key']  
PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"
IMAGE_SAVE_DIR = "pexels_images"

def pexels_search(query, count=8):
    """
    Returns a list of dicts:
      - title: str
      - thumbnail_url: str
      - content_url: str
      - source_page: str
    """
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
        raise RuntimeError("Set Pexels API key in env variable PEXELS_API_KEY or in this file.")
    headers = {
        "Authorization": PEXELS_API_KEY
    }
    params = {
        "query": query,
        "per_page": count
    }
    resp = requests.get(PEXELS_ENDPOINT, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Pexels search error {resp.status_code}: {resp.text}")
    data = resp.json()
    results = []
    for r in data.get("photos", []):
        results.append({
            "title": r.get("alt") or f"Photo by {r['photographer']}",
            "thumbnail_url": r["src"]["tiny"],
            "content_url": r["src"]["large2x"],
            "source_page": r["url"]
        })
    return results

def pexels_markdown(query, count=5):
    """Returns results as Markdown for UI/HTML display."""
    try:
        imgs = pexels_search(query, count)
    except Exception as e:
        return f"**Image search failed:** {e}"
    if not imgs:
        return f"No Pexels results found for '{query}'."
    out = ""
    for img in imgs:
        title = img["title"] or "Image"
        out += (
            f"**{title}**\n"
            f"[![img]({img['thumbnail_url']})]({img['content_url']})\n"
            f"[View on Pexels]({img['source_page']})\n\n"
        )
    return out.strip()

def download_image(url, fname):
    """Downloads image at url to fname."""
    r = requests.get(url, timeout=10)
    with open(fname, "wb") as f:
        f.write(r.content)
    return fname

def show_image_cli(url, save_prefix="image"):
    """Downloads and (if possible) displays image. Always saves thumbnail as file."""
    if not os.path.isdir(IMAGE_SAVE_DIR):
        os.makedirs(IMAGE_SAVE_DIR)
    basename = url.split("/")[-1].split("?")[0]
    fname = os.path.join(IMAGE_SAVE_DIR, f"{save_prefix}_{basename}")
    try:
        download_image(url, fname)
        print(f"Saved thumbnail as: {fname}")
    except Exception as e:
        print(f"Error saving {url}: {e}")
        return
    if Image and display:
        try:
            img = Image.open(fname)
            display(img)
        except Exception:
            print("(Could not display image inline. URL:)", url)

# ---------------- Stand-alone CLI for testing ---------------
if __name__ == "__main__":
    print("Pexels API image search demo")
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
        print("❌ Please set your PEXELS_API_KEY environment variable (see https://www.pexels.com/api/)")
        exit(1)
    while True:
        query = input("\nEnter image query (or :q to quit): ").strip()
        if not query or query == ":q":
            break
        try:
            images = pexels_search(query, count=5)
            for i, img in enumerate(images, 1):
                print(f"\n[{i}] {img['title']}\nPreview: {img['thumbnail_url']}\nFull: {img['content_url']}\nPage: {img['source_page']}")
                # Download and save thumbnail (and show if in Jupyter/IPython)
                show_image_cli(img['thumbnail_url'], save_prefix=f"{query.replace(' ','_').lower()}_{i}")
            print(f"\nMarkdown Preview (for AI/HTMLLabel):\n{pexels_markdown(query, count=2)}")
        except Exception as e:
            print(f"Error: {e}")
