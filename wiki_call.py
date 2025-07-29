import wikipedia
import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk import word_tokenize, pos_tag
import json

def extract_keywords(query):
    # Tokenize & POS tag
    stop_words = set(stopwords.words('english'))
    tokens = [w for w in word_tokenize(query) if w.isalnum() and w.lower() not in stop_words]
    tagged = pos_tag(tokens)
    keywords = [w for w, t in tagged if t in ['NN', 'NNS', 'NNP', 'NNPS']]
    if not keywords:
        keywords = tokens
    return keywords or [query[:30]]

def wiki_full_evidence(query, lang="en"):
    keywords = extract_keywords(query)
    search_phrase = ' '.join(keywords)
    wikipedia.set_lang(lang)
    out = {
        "queried_keywords": keywords,
        "article_title": None,
        "article_url": None,
        "text": None,
        "error": None
    }
    try:
        # Try direct search for keyword(s)
        results = wikipedia.search(search_phrase)
        if not results:
            raise ValueError("No Wikipedia results for keywords.")
        page = wikipedia.page(results[0])
        text = page.content.strip()
        # No truncation
        out.update({
            "article_title": page.title,
            "article_url": page.url,
            "text": text
        })
    except Exception as e:
        out["error"] = str(e)
    return out

# --- Example: Using from another program ---

if __name__ == "__main__":
    q = input("Enter your query: ")
    result = wiki_full_evidence(q)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Or just: print(result)
