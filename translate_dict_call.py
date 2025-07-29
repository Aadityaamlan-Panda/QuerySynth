import re
from deep_translator import GoogleTranslator
import nltk

try:
    from PyDictionary import PyDictionary
    pydict = PyDictionary()
except ImportError:
    pydict = None

from nltk.corpus import wordnet as wn

# Expand this as needed
lang_name_to_code = {
    'english': 'en',
    'hindi': 'hi',
    'french': 'fr',
    'bengali': 'bn',
    'spanish': 'es',
    'german': 'de'
}

def robust_translate(text, target_lang='en', source_lang='auto'):
    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        return {"original": text, "translated": translated, "target_lang": target_lang}
    except Exception as e:
        return {"error": f"Translation error: {e}"}

def get_definitions(word):
    word = word.strip().lower()
    defs = []
    if pydict and word.isalpha():
        try:
            defs_py = pydict.meaning(word)
            if defs_py:
                for pos, dlist in defs_py.items():
                    defs += [f"{pos}: {d}" for d in dlist if d]
        except Exception:
            pass
    if not defs:
        try:
            for syn in wn.synsets(word):
                d = syn.definition()
                if d not in defs:
                    defs.append(d)
            if not defs:
                defs.append(f"(No definition found for '{word}')")
        except Exception as e:
            defs.append(f"(WordNet error: {e})")
    return list(dict.fromkeys(defs))

def ai_def_translate(text, default_lang_code="en"):
    text_lower = text.lower()
    if text_lower.startswith('translate '):
        # Expected pattern: translate X to Y
        pattern = r"translate (.+?) to (\w+)"
        match = re.match(pattern, text_lower)
        if match:
            source_text = match.group(1).strip()
            target_lang_name = match.group(2).strip()
            target_lang_code = lang_name_to_code.get(target_lang_name.lower(), 'en')
            translation = robust_translate(source_text, target_lang=target_lang_code)
            return {"translation": translation, "definitions": []}
        else:
            translation = robust_translate(text, target_lang=default_lang_code)
            return {"translation": translation, "definitions": []}
    elif text_lower.startswith('define '):
        word_or_phrase = text[7:].strip()
        definitions = []
        if word_or_phrase.isalpha() and len(word_or_phrase.split()) == 1:
            definitions = get_definitions(word_or_phrase)
        return {"translation": {}, "definitions": definitions}
    else:
        translation = robust_translate(text, target_lang=default_lang_code)
        definitions = get_definitions(text) if text.isalpha() and len(text.split()) == 1 else []
        return {"translation": translation, "definitions": definitions}

def context_string_from_dict(result_dict):
    parts = []
    t = result_dict.get('translation', {})
    if "error" in t:
        parts.append(f"[Translation Error] {t['error']}")
    else:
        if t:
            parts.append(f"[Translation]\nOriginal: {t.get('original')}\nTranslated: {t.get('translated')} ({t.get('target_lang')})\n")
    defs = result_dict.get('definitions', [])
    if defs:
        parts.append("[Definition(s)]\n" + "\n".join(f"- {d}" for d in defs))
    return "\n".join(parts)

if __name__ == "__main__":
    print("Robust Translation & Dictionary module (NO TTS)")
    print("Uses deep-translator (Google Translate) and PyDictionary+WordNet.")
    query = input("Enter sentence or word to translate/define: ").strip()
    lang = "en"
    try:
        _ = wn.synsets("test")
    except LookupError:
        nltk.download('wordnet')
        nltk.download('omw-1.4')
    result = ai_def_translate(query, default_lang_code=lang)
    print("\n==== OUTPUT ====")
    print(context_string_from_dict(result))
