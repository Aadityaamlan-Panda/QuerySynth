import json
import os
import re

try:
    import difflib
except ImportError:
    difflib = None

try:
    import nltk
    from nltk.corpus import stopwords
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except Exception:
    nltk = None

_CODE_KB_PATH = os.path.join(os.path.dirname(__file__), "code_kb.json")
_code_kb = None
_last_best_match = None

def _load_code_kb():
    global _code_kb
    if _code_kb is None:
        with open(_CODE_KB_PATH, encoding="utf-8") as f:
            _code_kb = json.load(f)
    return _code_kb

def all_code_names():
    kb = _load_code_kb()
    return list(kb.keys())

def strip_instruction(text):
    text = text.strip()
    text = text.lower()
    patterns = [
        r'^(write (a )?(code|program|function|method)\s*(to|for|that|which|in python|in c\+\+|in c)?\s*)',
        r'^(give (me )?(the )?(code|program|implementation|solution)\s*(to|for|of)?\s*)',
        r'^(implement\s*)',
        r'^(find\s*(the)?\s*)',
        r'^(solve\s*)',
        r'^(print\s*)',
        r'^(how to\s*)'
    ]
    for pat in patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
    return text.strip(" .:?").title()

def _nltk_keywords(text):
    if not nltk:
        return set(w.lower() for w in re.findall(r'\w+', text))
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words('english'))
    tokens = nltk.word_tokenize(text)
    return set(w.lower() for w in tokens if w.isalpha() and w.lower() not in stop_words)

def _best_semantic_match(naked, kb):
    # Token overlap scoring for more context-aware match
    naked_kw = _nltk_keywords(naked)
    if not naked_kw:
        return None
    scores = []
    for code_name in kb.keys():
        name_kw = _nltk_keywords(code_name)
        overlap = naked_kw & name_kw
        jaccard = len(overlap) / float(len(naked_kw | name_kw) or 1)
        # Simple count and jaccard
        scores.append( (jaccard, len(overlap), code_name) )
    scores.sort(reverse=True)
    best_jaccard, best_overlap, best_name = scores[0]
    # Only accept good enough matches
    # If no strong jaccard, skip this step
    if best_jaccard > 0.45 or best_overlap >= 2:
        return best_name
    return None

def find_code_entry(user_query, fuzzy=True, cutoff=0.67):
    """
    Look up a code problem by user query.
    Uses prompt-stripping, fuzzy matching, and as a last resort, NLTK keyword/semantic similarity.
    Returns (actual_name, details) if found, else (None, None)
    """
    kb = _load_code_kb()
    global _last_best_match
    # Try direct match
    if user_query in kb:
        _last_best_match = user_query
        return user_query, kb[user_query]
    # Strip prompt, try again
    naked = strip_instruction(user_query)
    if naked in kb:
        _last_best_match = naked
        return naked, kb[naked]
    # Fuzzy match on stripped version
    if fuzzy and difflib and naked:
        candidates = list(kb.keys())
        matches = difflib.get_close_matches(naked, candidates, n=2, cutoff=cutoff)
        if matches:
            best = matches[0]
            _last_best_match = best
            return best, kb[best]
    # Fuzzy match original
    if fuzzy and difflib and user_query:
        candidates = list(kb.keys())
        matches = difflib.get_close_matches(user_query, candidates, n=1, cutoff=cutoff)
        if matches:
            best = matches[0]
            _last_best_match = best
            return best, kb[best]
    # If still not found: do a semantic/keyword-based NLTK match
    best_sem = _best_semantic_match(naked, kb)
    if best_sem and best_sem in kb:
        _last_best_match = best_sem
        return best_sem, kb[best_sem]
    return None, None

def get_code_info(name):
    _, details = find_code_entry(name)
    return details

def search_code_questions(query):
    """
    Return all codes whose question/approach contains the query (case-insensitive, supports partial/fuzzy search).
    """
    kb = _load_code_kb()
    results = []
    q = query.lower()
    for code_name, details in kb.items():
        if q in code_name.lower() or q in details.lower():
            results.append((code_name, details))
    return results

def as_markdown(name_or_query):
    """
    Return the code problem as markdown (split sections if possible).
    If not found, show best match if available.
    """
    actual, details = find_code_entry(name_or_query)
    if not details:
        return f"❌ No such code problem found for: `{name_or_query}`"
    sections = {
        "question": "",
        "approach": "",
        "complexity": "",
        "code": "",
        "other": ""
    }
    cur = "other"
    lines = details.splitlines()
    for line in lines:
        lstripped = line.lstrip("*/ ")
        if "**Question:**" in line or "Question:" in lstripped:
            cur = "question"
        elif "**Approach:**" in line or "Approach:" in lstripped:
            cur = "approach"
        elif "**Complexity" in line or "Complexity:" in lstripped:
            cur = "complexity"
        elif "**Code:**" in line or "Code:" in lstripped:
            cur = "code"
        if cur in sections and line.strip() not in sections[cur]:
            sections[cur] += line + "\n"
    md = ""
    for sec in ["question", "approach", "complexity", "code", "other"]:
        if sections[sec].strip():
            md += f"### {sec.title()}\n{sections[sec].strip()}\n"
    return md.strip() if md else details

# ----------------------- Stand-alone CLI ------------------------
if __name__ == "__main__":
    print("Loaded code_kb from:", _CODE_KB_PATH)
    print(f"Available problems: {len(all_code_names())}")

    while True:
        q = input("\nEnter code problem/query (or part of name, or ':ls' to list, or ':q' to quit): ").strip()
        if not q or q.lower() in [":q", "quit", "exit"]:
            break
        if q.lower() in [":ls", "list"]:
            for i, name in enumerate(all_code_names()):
                print(f"{i+1}. {name}")
            continue
        actual, details = find_code_entry(q)
        if not details:
            print("❌ No match found. Try a different query or ':ls' to list all.")
            continue
        print(f"\n========== Code Problem [{actual}] ==========")
        print(details)
        print("=============================================")
