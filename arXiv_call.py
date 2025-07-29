import requests
import feedparser
import html
import re

def clean_abstract(text):
    """Clean up LaTeX/math markup but DO NOT truncate."""
    text = re.sub(r'\\([a-zA-Z]+|,|;)', '', text)         # drop \emph etc
    text = re.sub(r'\$(.*?)\$', '', text)                 # remove math-mode inline
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    # No length truncation!
    return text

def search_arxiv(query, max_results=5):
    """
    Returns a list of dicts with arXiv paper metadata and cleaned abstract, for AI evidence injection.
    Each dict contains: title, summary, url, pdf, authors, published, id, for convenient prompting.
    """
    params = {
        'search_query': f'all:{query}',
        'start': 0,
        'max_results': max_results,
        'sortBy': 'lastUpdatedDate',
        'sortOrder': 'descending'
    }
    url = "http://export.arxiv.org/api/query"
    resp = requests.get(url, params=params, timeout=12)
    if resp.status_code != 200 or not resp.text.strip():
        raise RuntimeError(f"[arXiv API error] status={resp.status_code}: {resp.text[:200]}")
    feed = feedparser.parse(resp.text)
    results = []
    for entry in feed.entries:
        # Note: arxiv API uses Atom with some custom fields :)
        pdf_url = next((l.href for l in entry.links if 'pdf' in l.type or l.href.endswith('.pdf')), None)
        summary = clean_abstract(getattr(entry, 'summary', ''))
        first_author = entry.authors[0].name if entry.authors else ""
        authors = ', '.join(a.name for a in getattr(entry, 'authors', [])) if getattr(entry, 'authors', None) else ""
        results.append({
            "id": entry.get('id', None),
            "title": html.unescape(getattr(entry, 'title', '')).replace('\n', ' ').strip(),
            "summary": summary,
            "authors": authors,
            "first_author": first_author,
            "published": getattr(entry, 'published', ''),
            "updated": getattr(entry, 'updated', ''),
            "pdf": pdf_url,
            "link": getattr(entry, 'link', ''),
            "primary_category": getattr(entry, 'arxiv_primary_category', {}).get('term', None)
        })
    return results

def arxiv_results_to_prompt(evidence, context_maxlen=3200):
    """
    Converts result list into readable string for LLM context, truncated as needed for prompt.
    (This is ONLY used for LLM/injection, NOT for web/UI display)
    """
    blocks = []
    total_chars = 0
    for idx, r in enumerate(evidence):
        block = (
            f"[arXiv evidence {idx+1}]\n"
            f"Title: {r['title']}\n"
            f"Authors: {r['authors']}\n"
            f"Published: {r['published']}\n"
            f"Summary: {r['summary']}\n"
            f"PDF: {r['pdf']}\n"
            f"Link: {r['link']}\n"
        )
        # Only for AI prompt context: don't overflow the limit
        if total_chars + len(block) > context_maxlen:
            break
        blocks.append(block)
        total_chars += len(block)
    return '\n'.join(blocks)

# ------------ Example usage for RAG/AI injection ------------
if __name__ == "__main__":
    search_term = input("arXiv query: ")
    results = search_arxiv(search_term, max_results=3)
    import json
    # 1. Return as JSON list for pipeline
    print(json.dumps(results, ensure_ascii=False, indent=2))
    # 2. Or, as readable string for prompt context:
    print("\n=== FOR AI PROMPT INJECTION ===\n")
    print(arxiv_results_to_prompt(results, 3200))
