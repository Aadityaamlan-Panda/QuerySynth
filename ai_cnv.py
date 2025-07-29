import os
import json
import tempfile
import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
import nltk
import re
import markdown2
from tkhtmlview import HTMLLabel
from PIL import Image, ImageTk
import pygame
pygame.mixer.init()

# --- Evidence modules ---
import arXiv_call
import govt_call
import news_call
import SOSX_call
import translate_dict_call
import weather_call
import wiki_call
import wolfram_call
import yt_list_call
import ollama_int
from translate_dict_call import context_string_from_dict
import code_call
import image_call

CONV_HISTORY_FILE = "conversation_history.json"
USER_COLOR  = "#215D91"
USER_BG     = "#EDF4FC"
AI_COLOR    = "#218840"
AI_BG       = "#F1FBF0"
BORDER      = "#DDEAF4"
SRC_BG      = "#F5F8FA"
SRC_LABEL   = "#19546A"
FONT_USER = ("Segoe UI", 11, "bold")
FONT_AI   = ("Segoe UI", 11, "italic")
FONT_META = ("Segoe UI", 9)
FONT_MSG  = ("Consolas", 11)
FONT_BTN  = ("Segoe UI", 11)

def save_conversation(history):
    try:
        with open(CONV_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save conversation:", e)

def load_conversation():
    if os.path.exists(CONV_HISTORY_FILE):
        try:
            with open(CONV_HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def render_context_block(blk):
    if isinstance(blk, dict):
        if 'translation' in blk or 'definitions' in blk:
            return context_string_from_dict(blk)
        show_keys = [
            'title', 'summary', 'question_title', 'definition',
            'snippet', 'description', 'text', 'answer', 'answers'
        ]
        lines = []
        for k in show_keys:
            if k in blk and blk[k]:
                if isinstance(blk[k], (list, tuple)):
                    lines.append(f"**{k.capitalize()}**: " + "; ".join(str(x) for x in blk[k]))
                else:
                    lines.append(f"**{k.capitalize()}**: {blk[k]}")
        if lines:
            return "\n\n".join(lines)
        return str(blk)
    return str(blk)

def extract_intents_and_keywords(query, conversation=None):
    """
    Improved: Strictly NLTK and phrase-based with NO substring fuzzy matching.
    Return highest scoring sources via exact token match or phrase triggers only.
    """
    lowered = query.lower().strip()
    if conversation:
        context_buffer = " ".join(x["content"] for x in conversation[-6:] if x["role"] in ["user", "assistant"])
        lowered += " " + context_buffer

    # Priority triggers: phrase-first, then token
    priority_triggers = [
    ("wiki", [
        "explain", "definition", "define", "who is", "what is", "describe", "explanation", 
        "meaning", "summarize", "history of", "who was", "tell me about", 
        "give a summary", "give information about"
    ]),

    ("yt", [
        "play music", "play song", "play video", "listen to", "play soundtrack",
        "watch video", "youtube", "music", "song", "audio", "video song",
        "play movie", "watch movie", "show music video", "show song video"
    ]),

    ("code", [
        "write code", "code for", "show code", "implement", "give code", 
        "program for", "source code", "solution for", "provide code", 
        "generate code", "write a program", "example code", "python code",
        "give me code", "give java code", "give c code", "display code"
    ]),

    ("image", [
        "show images", "show me images", "show me photos", "show me pictures", "find an image",
        "show image", "show photo", "give me an image", "wallpaper of", "display images",
        "image of", "show a photo of", "give picture", "show visuals", "pictures of", "photos of",
        "show me a visual", "show me a wallpaper", "download an image", "show me wallpapers",
        "show pictures", "display a photo", "display a picture", "display a wallpaper"
    ]),
     ("news", [
        "news about", "latest news", "current events", "breaking story", "what happened in", 
        "top stories", "headlines in", "sports news", "politics story", "recent update"
    ]),
    ("arxiv", [
        "find a research paper", "academic article", "search publication", 
        "journal paper", "preprint on", "give me study", "latest research on", "scientific article"
    ]),
    ("weather", [
        "weather today", "what's the weather", "temperature in", "forecast for", 
        "will it rain", "weather update", "humidity in", "air quality"
    ]),
    ("wolfram", [
        "calculate", "solve", "integrate", "differentiate", "plot", "math solution", 
        "compute", "find result of", "equation for", "show calculation"
    ]),
    ("govt", [
        "census data", "government statistics", "ministry report", "data.gov info", 
        "mandi prices", "statistical report", "indian budget", "govt policy"
    ]),
    ("translate_dict", [
        "translate", "meaning of", "definition of", "how to say", "translate word", 
        "synonym for", "antonym of", "pronunciation of"
    ]),
    
    # You can add more sources/trigger-phrases as needed.
    # For Indian/regional varieties:
    # ("image", ["pic of", "show snap of", "show selfie of", ...]),
]

    source_mappings = {
        "arxiv": ["arxiv", "paper", "abstract", "research", "journal", "preprint", "publication", "scientific", "study", "arxiv.org"],
        "news": ["news", "headline", "breaking", "report", "article", "latest", "current events", "news article", "news report", "news update", "news story", "news summary", "news analysis", "news coverage", "news briefing", "news bulletin", "news release", "news piece"],
        "govt": ["census", "government", "india", "ministry", "statistical", "data.gov", "mandi", "upi", "govdata", "govt data", "government data", "official data", "public data", "government statistics", "government information"],
        "weather": ["weather", "temperature", "forecast", "humidity", "rain", "aqi", "climate", "meteorological", "weather report", "weather forecast", "weather conditions", "weather update", "weather information", "current weather", "local weather"],
        "wiki": ["wikipedia", "wiki", "encyclopedia", "information", "knowledge", "article", "define", "explain", "who is", "what is", "describe", "explanation", "meaning", "summarize", "history of", "wiki article", "wiki page", "wikipedia page", "wikipedia article", "wikipedia entry",],
        "stackex": ["stackoverflow", "stackexchange", "so", "code", "error", "python", "c++", "java", "implementation", "algorithm", "syntax", "question", "answer", "programming", "developer", "programmer", "software", "coding", "debugging", "stackoverflow question", "stackoverflow answer", "stackexchange question", "stackexchange answer"],
        "wolfram": ["calculate", "integrate", "derivative", "equation", "solve", "math", "plot", "compute", "alpha", "wolfram", "wolfram alpha", "wolframalpha", "wolfram query", "wolfram computation", "wolfram calculation", "wolfram result", "wolfram answer"],
        "translate_dict": ["translate", "dictionary", "translation", "pronounce", "synonym", "antonym", "meaning", "definition", "dict"], 
        "yt": ["youtube", "video", "soundtrack", "mp3","play", "listen", "audio", "clip", "music", "song", "youtube video", "youtube audio", "youtube clip", "youtube music", "youtube song"],
        "image": ["image", "images", "picture", "pictures", "photo", "photos", "pic", "visual", "wallpaper", "pexels", "pexels image", "pexels photo", "pexels picture", "pexels visual", "pexels wallpaper"],
        "code": ["code", "algorithm", "implementation", "program", "function", "script", "source code", "coding", "programming", "software development", "software engineering", "code snippet", "code example", "code implementation", "code solution", "code sample", "code block"],
    }
    # Check the phrase triggers first, in order, with boundaries
    for src, phrases in priority_triggers:
        for phrase in phrases:
            if re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
                return [src], [phrase]

    # NLTK tokens only
    try:
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [w for w in nltk.word_tokenize(lowered) if w.isalnum() and w.lower() not in stop_words]
    except Exception:
        tokens = lowered.split() # crude backup
    
    matched_sources = set()
    score_map = {key: 0 for key in source_mappings}
    # Token/POS-driven intent
    for src, wordlist in source_mappings.items():
        for w in wordlist:
            if w in tokens: # Exact token match only
                matched_sources.add(src)
                score_map[src] += 3

    # If no matches, return wiki only as a fallback (never ranks higher than a real token match)
    if not matched_sources:
        return ["wiki"], []
    uniq = sorted(matched_sources, key=lambda s: -score_map[s])
    return uniq, tokens

def fetch_context_for_query(query, max_sources=3, conversation=None):
    sources, keywords = extract_intents_and_keywords(query, conversation)
    fetch_map = {
        "arxiv": lambda q: arXiv_call.search_arxiv(q, max_results=3),
        "news": lambda q: news_call.fetch_all_news(q, num_articles=2),
        "govt": lambda q: govt_call.govdata_ai_search(q),
        "weather": lambda q: weather_call.fetch_weather(q),
        "wiki": lambda q: wiki_call.wiki_full_evidence(q),
        "stackex": lambda q: SOSX_call.sose_query_to_answers_json(q),
        "wolfram": lambda q: wolfram_call.query_wolfram(q),
        "translate_dict": lambda q: translate_dict_call.ai_def_translate(q, default_lang_code="en"),
        "yt": lambda q: yt_list_call.download_youtube_audio(q, outdir="./", output_filename="yt_clip"),
        "code": lambda q: {"title": "Code Search Result", "text": code_call.as_markdown(q)},
        "image": lambda q: {"title": "Image Results", "text": image_call.pexels_markdown(q, count=6)},
    }
    blocks = []
    for src in sources[:max_sources]:
        if src in fetch_map:
            try:
                evidence = fetch_map[src](query)
                blocks.append((src, evidence))
            except Exception as e:
                blocks.append((src, f"[Error fetching {src}: {e}]"))
    return blocks, sources

def extract_links_from_evidence(evidence):
    links = []
    if isinstance(evidence, list):
        for e in evidence:
            links += extract_links_from_evidence(e)
    elif isinstance(evidence, dict):
        title = (evidence.get('title') or evidence.get('question_title') or evidence.get('match_title') or evidence.get('original') or '...')
        url = (evidence.get('url') or evidence.get('link') or evidence.get('pdf') or evidence.get('question_link') or evidence.get('source_page'))
        if url and isinstance(url, str) and url.startswith("http"):
            links.append((title, url))
    elif isinstance(evidence, str):
        urls = re.findall(r'https?://\S+', evidence)
        for u in urls:
            links.append((u[:70], u))
    return links

def get_preview(text, maxlen=90):
    txt = text.replace('\r','').replace('\n\n', ' ').replace('\n', ' ')
    s = txt[:maxlen]
    idx = s.rfind('. ')
    if idx > 20:
        s = s[:idx+1]
    if len(s) < len(txt): s += " ..."
    return s.strip()

class RAGFrontendTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QuerySynth - Your Local AI Assistant")
        self.geometry("1230x860")
        self.configure(bg="#eaf5fa")
        self.resizable(True, True)
        self.links = []
        self.audio_ctrl_window = None
        self.ollama_models = ollama_int.list_models()
        self.selected_model = tk.StringVar(value=self.ollama_models[0] if self.ollama_models else "")
        self.conversation = load_conversation()
        self._setup_widgets()
        self.web_blocks = []
        self._tk_img_refs = []

    def _setup_widgets(self):
        main = ttk.Frame(self, padding=(10,6))
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(main)
        right.pack(side="right", fill="y", expand=False)

        model_row = ttk.Frame(left)
        model_row.pack(padx=2, pady=2, fill="x")
        ttk.Label(model_row, text="Ollama Model:", font=FONT_META).pack(side="left")
        model_dropdown = ttk.Combobox(
            model_row, values=self.ollama_models, textvariable=self.selected_model,
            state="readonly", width=22, font=FONT_BTN
        )
        model_dropdown.pack(side="left", padx=3)
        self.mode = tk.StringVar(value="AI+RAG")
        ttk.Button(model_row, text="💬 Chat", width=10, command=lambda: self.set_mode("Chat")).pack(side="left", padx=(12,0))
        ttk.Button(model_row, text="🔎 Search", width=12, command=lambda: self.set_mode("Search")).pack(side="left", padx=2)
        ttk.Button(model_row, text="🤖 AI + RAG", width=14, command=lambda: self.set_mode("AI+RAG")).pack(side="left", padx=2)
        self.mode_label = ttk.Label(model_row, text="Mode: AI+RAG", font=FONT_META, foreground="#6A5ACD")
        self.mode_label.pack(side="left", padx=(16,2))
        ttk.Button(model_row, text="🔄 Refresh Chat", width=16, command=self.refresh_conversation).pack(side="left", padx=10)

        conv_frame = tk.Frame(left, bg="#f7fbff")
        conv_frame.pack(fill="both", expand=True, padx=4, pady=(2,2))
        self.conv_text = tk.Text(conv_frame, wrap="word", font=("Consolas", 12), bg="#f7fbff", bd=0, height=18)
        self.conv_text.pack(side="left", fill="both", expand=True)
        self.conv_text.tag_configure("user", foreground=USER_COLOR, font=FONT_USER)
        self.conv_text.tag_configure("assistant", foreground=AI_COLOR, font=FONT_AI)
        self.conv_text.config(state="disabled")
        conv_scroll = ttk.Scrollbar(conv_frame, command=self.conv_text.yview)
        conv_scroll.pack(side="right", fill="y")
        self.conv_text['yscrollcommand'] = conv_scroll.set

        entry_row = ttk.Frame(left)
        entry_row.pack(fill='x', padx=2, pady=(6,2))
        self.query_entry = ttk.Entry(entry_row, font=("Consolas", 13), width=54)
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(1,4))
        self.query_entry.bind('<Return>', lambda e: self.on_submit_query())
        ttk.Button(entry_row, text="👉 Send", command=self.on_submit_query).pack(side="left", padx=2)

        self.source_label = ttk.Label(right, text="Sources & Links", font=("Segoe UI", 12, "bold"), foreground=SRC_LABEL)
        self.source_label.pack(padx=2, pady=(8,1), anchor="w")
        sources_frame = tk.Frame(right, bg=SRC_BG)
        sources_frame.pack(fill="y", expand=False, padx=2, pady=(0,8))
        self.result_canvas = tk.Canvas(sources_frame, bg=SRC_BG, height=322, width=442, highlightthickness=0, bd=0)
        self.result_canvas.pack(side="left", fill="y", expand=False)
        self.scrollbar = ttk.Scrollbar(sources_frame, orient="vertical", command=self.result_canvas.yview)
        self.scrollbar.pack(side="right", fill="y", padx=0)
        self.result_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.web_result_list = tk.Frame(self.result_canvas, bg=SRC_BG)
        self.web_result_list.bind("<Configure>", lambda e: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all")))
        self.result_canvas.create_window((0,0), window=self.web_result_list, anchor="nw")

        ttk.Label(right, text="───────", font=("Consolas", 10)).pack()
        ttk.Label(right, text="🔗 Relevant Links", font=("Segoe UI", 11, "bold")).pack()
        self.link_listbox = tk.Listbox(
            right, width=45, height=10, font=("Consolas",11), activestyle='none', bg="#effafd", borderwidth=1
        )
        self.link_listbox.pack(padx=4, pady=1, fill="both", expand=True)
        self.link_listbox.bind('<Double-1>', self.open_selected_link)
        self._refresh_conversation()

    def _scroll_conversation_to_end(self, event=None):
        self.conv_text.see("end")

    def set_mode(self, mode):
        self.mode.set(mode)
        self.mode_label.config(text=f"Mode: {mode}")

    def on_submit_query(self):
        q = self.query_entry.get().strip()
        if not q: return
        user_msg = {"role": "user", "content": q}
        self.conversation.append(user_msg)
        save_conversation(self.conversation)
        self.query_entry.delete(0, tk.END)
        self._refresh_conversation()
        for child in self.web_result_list.winfo_children():
            child.destroy()
        self.link_listbox.delete(0, tk.END)
        threading.Thread(target=self._handle_conversation, args=(q, self.mode.get()), daemon=True).start()

    def _refresh_conversation(self):
        self.conv_text.config(state="normal")
        self.conv_text.delete('1.0', tk.END)
        for msg in self.conversation[-60:]:
            role = msg["role"]
            txt = msg["content"]
            tag = "user" if role == "user" else "assistant"
            self.conv_text.insert(tk.END, f"{'User:' if tag=='user' else 'Assistant:'} ", tag)
            self.conv_text.insert(tk.END, f"{txt}\n", tag)
        self.conv_text.config(state="disabled")
        self._scroll_conversation_to_end()

    def refresh_conversation(self):
      """Delete conversation_history.json and clear the chat/history panel."""
      try:
        if os.path.exists(CONV_HISTORY_FILE):
            os.remove(CONV_HISTORY_FILE)
      except Exception as e:
        print(f"Error deleting conversation file: {e}")
      self.conversation = []
      self._refresh_conversation()


    def _add_conv_bubble(self, role, text):
        pass

    def _handle_conversation(self, user_query, mode):
        sources_data = []
        ai_reply = None
        audio_files = []
        if mode == "Chat":
            ai_reply = self._ai_only_reply(user_query)
        elif mode == "Search":
            sources_data, links, audio_files = self._external_only_search(user_query)
        else:
            sources_data, links, ai_reply, audio_files = self._ai_rag_reply(user_query)
        if ai_reply is not None:
            self.conversation.append({"role": "assistant", "content": ai_reply})
            save_conversation(self.conversation)
        self.after(0, self._refresh_conversation)
        self.after(0, lambda: self.display_sources_and_links(sources_data, autostart_audio=bool(audio_files), audio_files=audio_files))

    def _ai_only_reply(self, query):
        ai_model = self.selected_model.get()
        conv_history = [{"role": x["role"], "content": x["content"]} for x in self.conversation if x["role"] in ["user", "assistant"]][-12:]
        prompt = ""
        for m in conv_history[-11:]:
            who = "User" if m["role"] == "user" else "Assistant"
            prompt += f"{who}: {m['content']}\n"
        prompt += f"User: {query}\nAssistant:"
        ai_ans = ollama_int.ask_ai(prompt, model=ai_model)
        return str(ai_ans)

    def _external_only_search(self, query):
        context_blocks, _ = fetch_context_for_query(query, max_sources=3, conversation=self.conversation)
        url_links, found_audio = [], []
        for src,evidence in context_blocks:
            filepaths = []
            if isinstance(evidence, list):
                filepaths = [blk for blk in evidence if isinstance(blk, str) and blk.strip().lower().endswith('.mp3') and os.path.exists(blk.strip())]
            elif isinstance(evidence, str) and evidence.strip().lower().endswith('.mp3') and os.path.exists(evidence):
                filepaths = [evidence.strip()]
            if filepaths:
                found_audio.extend(filepaths)
        return context_blocks, [], found_audio

    def _ai_rag_reply(self, query):
        context_blocks, _ = fetch_context_for_query(query, max_sources=3, conversation=self.conversation)
        all_blocks = []
        url_links, found_audio = [], []
        for src, evidence in context_blocks:
            block_list = evidence if isinstance(evidence, list) else [evidence]
            for blk in block_list:
                txt = render_context_block(blk)
                all_blocks.append((src, txt, blk))
                if isinstance(blk, str) and blk.strip().lower().endswith('.mp3'):
                    mp3 = blk.strip()
                    if os.path.exists(mp3):
                        found_audio.append(mp3)
            url_links += extract_links_from_evidence(evidence)
        self.web_blocks = all_blocks
        messages = [{"role": x["role"], "content": x["content"]} for x in self.conversation][-10:]

        conv_context = "\n".join(
        f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in messages[-6:])

        evidence_parts = []
        for src, txt, _ in all_blocks:
          evidence_parts.append(f"[{src.upper()}]\n{txt}\n")
        evidence_context = "\n------\n".join(evidence_parts)

        prompt = f"""\
You are an AI assistant that answers user queries using real-world sources and documents.

- Use the Sources context below to answer the User question as **factually and directly as possible**.
- If possible, mention the module name in your answer where relevant (e.g., [NEWS], [WIKI], [IMAGE], [CODE], etc.).
- If the answer is not supported or incomplete in the retrieved Sources, explain that briefly, and do NOT hallucinate details.
- If the user is looking for audio, image, code, or other special content, refer to the results in the Sources context section.
- Stay concise, professional, and Indian English friendly if appropriate.
- If relevant, summarize key info into bullet points.
- Do NOT repeat the question, just answer it clearly.

User Query:
{query}

{"Recent Conversation (last turns):\n" + conv_context if conv_context else ""}

Sources context:
{evidence_context}

Your answer:
"""
        ai_ans = ollama_int.ask_ai(prompt, model=self.selected_model.get())
        return context_blocks, url_links, str(ai_ans), found_audio

    def display_sources_and_links(self, context_blocks, autostart_audio=False, audio_files=None):
        for child in self.web_result_list.winfo_children():
            child.destroy()
        self._tk_img_refs = []
        self.cards_evidence = []
        for idx, (src, evidence) in enumerate(context_blocks):
            card = tk.Frame(self.web_result_list, bg=SRC_BG, bd=1, relief="ridge")
            card.pack(side="top", fill="x", expand=True, padx=2, pady=5, anchor="n")
            tk.Label(card, text=src.upper(), font=("Segoe UI", 9, "bold"),
                     fg="#376A98", bg=SRC_BG).pack(anchor="w", padx=6, pady=(1,0))
            full_blocks = evidence if isinstance(evidence, list) else [evidence]
            first_blk = full_blocks[0] if full_blocks else evidence
            self.cards_evidence.append((src, full_blocks))

            def make_card_callback(blocks=full_blocks, src=src, card_frame=card):
                def card_callback(ev=None):
                    orig_bg = card_frame['bg']
                    card_frame['bg'] = '#C8E6C9'
                    card_frame.after(120, lambda: card_frame.config(bg=orig_bg))
                    def in_thread():
                        html_body = ""
                        for b in blocks:
                            txt = render_context_block(b)
                            html_body += markdown2.markdown(txt) + "<hr>"
                        html_content = (
                            "<meta charset='utf-8'>"
                            f"<title>{src.upper()} - Full Source</title>"
                            "<body style='font-family: Segoe UI, Arial, sans-serif; font-size: 15px; background: #f7fbfa;'>"
                            + html_body + "</body>"
                        )
                        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                            f.write(html_content)
                            filename = f.name
                        self.after(0, lambda: webbrowser.open('file://' + os.path.abspath(filename)))
                    threading.Thread(target=in_thread, daemon=True).start()
                return card_callback

            if src == "image" and hasattr(image_call, "get_last_filenames"):
                img_filenames = image_call.get_last_filenames()
                if img_filenames:
                    img_row = tk.Frame(card, bg=SRC_BG)
                    img_row.pack(anchor="w", padx=4, pady=3, fill="x")
                    for img_fname in img_filenames:
                        img_path = os.path.join("pexels_images", img_fname)
                        try:
                            pil_img = Image.open(img_path)
                            pil_img.thumbnail((110, 90))
                            tk_img = ImageTk.PhotoImage(pil_img)
                            lbl = tk.Label(img_row, image=tk_img, bg=SRC_BG, cursor="hand2", bd=1, relief="groove")
                            lbl.pack(side="left", padx=2, pady=2)
                            self._tk_img_refs.append(tk_img)
                        except Exception: pass
                else:
                    tk.Label(card, text="No images found.", bg=SRC_BG).pack()
            else:
                txt = render_context_block(first_blk)
                preview = get_preview(txt, maxlen=120) if src != "code" else txt
                html_preview = markdown2.markdown(preview) if src != "code" else markdown2.markdown(txt)
                preview_label = HTMLLabel(card, html=html_preview, background=SRC_BG, width=56, height=4 if src=="code" else 2)
                preview_label.pack(fill="x", padx=6, pady=(2, 2))
            card.bind("<Button-1>", make_card_callback(full_blocks, src, card))

        self.link_listbox.delete(0, tk.END)
        links = []
        for src, evidence in context_blocks:
            links += extract_links_from_evidence(evidence)
        for title, url in links:
            display_title = title or url
            display_title = (display_title[:100] + " ...") if len(display_title) > 100 else display_title
            self.link_listbox.insert(tk.END, display_title)
        self.links = links
        if autostart_audio and audio_files:
            self.play_audio(audio_files[0])

    def audio_player_window(self, audio_file):
        try:
            if self.audio_ctrl_window is not None and self.audio_ctrl_window.winfo_exists():
                self.audio_ctrl_window.destroy()
        except Exception: pass
        self.audio_ctrl_window = tk.Toplevel(self)
        self.audio_ctrl_window.title("Audio Player")
        self.audio_ctrl_window.geometry("400x120")
        self.audio_ctrl_window.resizable(False, False)
        ttk.Label(self.audio_ctrl_window, text=f"Playing: {os.path.basename(audio_file)}", font=("Segoe UI", 11, "bold")).pack(pady=6)
        state_label = ttk.Label(self.audio_ctrl_window, text="[Playing]", font=("Segoe UI", 9, "italic"), foreground="#287")
        state_label.pack()
        btn_frame = ttk.Frame(self.audio_ctrl_window)
        btn_frame.pack(pady=4)
        def pause():
            pygame.mixer.music.pause()
            state_label.config(text="[Paused]")
        def resume():
            pygame.mixer.music.unpause()
            state_label.config(text="[Playing]")
        def stop():
            pygame.mixer.music.stop()
            state_label.config(text="[Stopped]")
        ttk.Button(btn_frame, text="⏸ Pause", width=10, command=pause).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="▶ Resume", width=10, command=resume).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="■ Stop", width=10, command=stop).pack(side="left", padx=5)
        ttk.Button(self.audio_ctrl_window, text="Close Player", command=lambda:[stop(), self.audio_ctrl_window.destroy()]).pack(pady=5)

    def play_audio(self, audio_file):
        def _play():
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
            except Exception as e:
                self.show_info(f"Could not play audio: {e}")
        threading.Thread(target=_play, daemon=True).start()
        self.after(200, lambda: self.audio_player_window(audio_file))

    def open_selected_link(self, event):
        idx_tuple = self.link_listbox.curselection()
        if idx_tuple:
            idx = idx_tuple[0]
            if self.links and 0 <= idx < len(self.links):
                url_info = self.links[idx]
                url = url_info[1] if isinstance(url_info, (tuple, list)) and len(url_info) > 1 else url_info
                if url:
                    webbrowser.open(url)

    def show_info(self, msg):
        self.conversation.append({"role": "assistant", "content": f"[Info] {msg}"})
        self._refresh_conversation()
        save_conversation(self.conversation)

if __name__ == "__main__":
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('punkt')
        nltk.download('stopwords')
        nltk.download('averaged_perceptron_tagger')
    RAGFrontendTk().mainloop()
