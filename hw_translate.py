"""HANGUL WOOD translation engine: English in, Hangul out.
Offline: built-in English->Korean neural model (CTranslate2 + SentencePiece), always available.
Online (optional, Auto mode): HTTPS translation for higher quality; falls back to the built-in model on any failure.
Whole text is translated exactly as typed (online first in Auto), built-in model as offline backup
(so tiny ambiguous queries never hallucinate unrelated meanings).
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import json, os, re, ssl, sys, threading, time, urllib.parse, urllib.request
from collections import OrderedDict

HANGUL_RE = re.compile(r"[\uac00-\ud7a3\u3131-\u318e]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
# Tiny leftover Latin fragments that must never be phonetic-Hangulized into junk (e.g. "i"+"ts" -> i트스).
TINY_LATIN_RE = re.compile(r"(?<![A-Za-z])([A-Za-z]{1,2})(?![A-Za-z])")

# Short phrases go glossary -> offline -> (online only if long enough). Online alone stays online-first.
SHORT_WORD_LIMIT = 3          # 1–3 words: treat as short
SHORT_CHAR_LIMIT = 24         # or very short character count
ONLINE_MIN_WORDS = 4          # Auto: need this many words (or a sentence end) before trying online
ONLINE_MIN_CHARS = 28


def res(*p):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *p)


def _ssl_ctx():
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)          # Windows certificate store, verification ON
    except Exception:
        pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


# ---------------------------------------------------------------- short-phrase glossary (checked BEFORE any MT / phonetic)
# Keys are lowercased, apostrophes kept. Multi-word phrases listed as whole entries.
GLOSSARY = {
    # greetings / politeness
    "hi": "안녕",
    "hello": "안녕하세요",
    "hey": "야",
    "bye": "안녕",
    "goodbye": "안녕히 가세요",
    "good bye": "안녕히 가세요",
    "thanks": "고마워",
    "thank you": "고마워요",
    "thank you!": "고마워요!",
    "thx": "고마워",
    "sorry": "미안",
    "i'm sorry": "미안해요",
    "im sorry": "미안해요",
    "please": "부탁해요",
    "yes": "네",
    "yeah": "응",
    "yep": "응",
    "no": "아니요",
    "nope": "아니",
    "ok": "괜찮아",
    "okay": "괜찮아",
    "okey": "괜찮아",
    "good morning": "좋은 아침",
    "good night": "잘 자",
    "good evening": "좋은 저녁",
    "how are you": "어떻게 지내?",
    "how's it going": "잘 지내?",
    "nice to meet you": "만나서 반가워",
    # contractions (never emit Latin leftovers like i트스)
    "it's": "그건",
    "it is": "그것은",
    "i'm": "나는",
    "i am": "나는",
    "don't": "하지 마",
    "do not": "하지 마",
    "can't": "못해",
    "cannot": "못해",
    "that's": "그건",
    "that is": "그것은",
    "there's": "있어",
    "there is": "있어",
    "i'll": "내가 할게",
    "i will": "내가 할게",
    "we'll": "우리가 할게",
    "we will": "우리가 할게",
    "you're": "너는",
    "you are": "너는",
    "we're": "우리는",
    "we are": "우리는",
    "he's": "그는",
    "he is": "그는",
    "she's": "그녀는",
    "she is": "그녀는",
    "isn't": "아니야",
    "aren't": "아니야",
    "wasn't": "아니었어",
    "weren't": "아니었어",
    "won't": "안 할게",
    "wouldn't": "안 할 거야",
    "couldn't": "못했어",
    "shouldn't": "하면 안 돼",
    "didn't": "안 했어",
    "doesn't": "안 해",
    "haven't": "안 했어",
    "hasn't": "안 했어",
    "hadn't": "안 했었어",
    "let's": "하자",
    "who's": "누구야",
    "what's": "뭐야",
    "where's": "어디야",
    "when's": "언제야",
    "why's": "왜야",
    "how's": "어때",
    # clothing / nouns MT often mangles when alone
    "hood": "후드",
    "hoodie": "후드티",
    "hoodies": "후드티",
    "hat": "모자",
    "cap": "모자",
    "shirt": "셔츠",
    "t-shirt": "티셔츠",
    "tshirt": "티셔츠",
    "jacket": "자켓",
    "coat": "코트",
    "pants": "바지",
    "shoes": "신발",
    "socks": "양말",
    "dress": "드레스",
    "skirt": "치마",
    "sweater": "스웨터",
    "jeans": "청바지",
    # common tiny words that go weird alone
    "bear": "곰",
    "i": "나",
    "you": "너",
    "me": "나",
    "we": "우리",
    "they": "그들",
    "he": "그",
    "she": "그녀",
    "it": "그것",
    "the": "그",
    "a": "하나의",
    "an": "하나의",
    "and": "그리고",
    "or": "또는",
    "but": "하지만",
    "so": "그래서",
    "if": "만약",
    "this": "이것",
    "that": "저것",
    "here": "여기",
    "there": "거기",
    "now": "지금",
    "today": "오늘",
    "tomorrow": "내일",
    "yesterday": "어제",
    "love": "사랑",
    "like": "좋아해",
    "want": "원해",
    "need": "필요해",
    "help": "도와줘",
    "stop": "멈춰",
    "go": "가",
    "come": "와",
    "wait": "기다려",
    "good": "좋아",
    "bad": "나빠",
    "great": "대단해",
    "cool": "멋져",
    "wow": "와",
    "yes please": "네, 부탁해요",
    "no thanks": "아니, 괜찮아",
    "excuse me": "실례합니다",
    "of course": "물론이지",
    "all right": "좋아",
    "alright": "좋아",
}

# Known English tokens: never phonetic-Hangulize these leftovers; map via glossary or leave for re-translate.
COMMON_ENGLISH = set(GLOSSARY.keys()) | {
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", "shall", "can", "to", "of", "in",
    "on", "at", "for", "with", "from", "by", "as", "into", "about", "up", "out", "just", "not",
    "my", "your", "his", "her", "our", "their", "its", "mine", "yours", "ours", "theirs",
    "what", "who", "where", "when", "why", "how", "which", "whom", "whose",
    "all", "any", "some", "many", "much", "more", "most", "other", "another", "each", "every",
    "very", "really", "too", "also", "only", "even", "still", "already", "again", "always", "never",
    "thing", "things", "time", "day", "way", "man", "woman", "people", "person", "friend", "name",
    "game", "play", "make", "made", "get", "got", "see", "saw", "know", "think", "say", "said",
    "look", "take", "give", "find", "tell", "ask", "work", "call", "try", "use", "feel", "leave",
    "put", "keep", "let", "begin", "seem", "help", "show", "hear", "run", "move", "live", "believe",
    "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose", "pay", "meet", "include",
    "continue", "set", "learn", "change", "lead", "understand", "watch", "follow", "stop", "create",
    "speak", "read", "allow", "add", "spend", "grow", "open", "walk", "win", "offer", "remember",
    "love", "consider", "appear", "buy", "wait", "serve", "die", "send", "expect", "build", "stay",
    "fall", "cut", "reach", "kill", "remain", "suggest", "raise", "pass", "sell", "require", "report",
    "decide", "pull", "ts", "st", "th", "ll", "re", "ve", "nt", "s", "t", "d", "m",
}


def normalize_key(text):
    """Lowercase + collapse spaces; keep apostrophes for contraction keys."""
    s = text.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" \t\r\n\"“”‘’")
    # drop a single trailing . ! ? for glossary lookup (keep internal punctuation)
    if len(s) > 1 and s[-1] in ".!?":
        s = s[:-1].rstrip()
    return s


def glossary_lookup(text):
    """Exact short-phrase hit, or None."""
    key = normalize_key(text)
    if not key:
        return None
    hit = GLOSSARY.get(key)
    if hit is not None:
        return hit
    # bare punctuation variants already stripped; try without trailing comma
    if key.endswith(","):
        return GLOSSARY.get(key[:-1].rstrip())
    return None


def word_count(text):
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text))


def is_short_input(text):
    src = text.strip()
    if not src:
        return True
    wc = word_count(src)
    return wc <= SHORT_WORD_LIMIT or len(src) <= SHORT_CHAR_LIMIT


def looks_like_sentence(text):
    """Long enough / has sentence end — safe to try context-free online MT."""
    src = text.strip()
    if re.search(r"[.!?](?:\s|$)", src):
        return word_count(src) >= 2 or len(src) >= 12
    return word_count(src) >= ONLINE_MIN_WORDS or len(src) >= ONLINE_MIN_CHARS


def expand_contractions_for_mt(text):
    """Expand common contractions before neural MT so leftovers never stay as it's/I'm fragments."""
    mapping = [
        (r"\bwon't\b", "will not"), (r"\bcan't\b", "cannot"), (r"\bshan't\b", "shall not"),
        (r"\bI'm\b", "I am"), (r"\bI've\b", "I have"), (r"\bI'd\b", "I would"), (r"\bI'll\b", "I will"),
        (r"\byou're\b", "you are"), (r"\byou've\b", "you have"), (r"\byou'd\b", "you would"), (r"\byou'll\b", "you will"),
        (r"\bhe's\b", "he is"), (r"\bshe's\b", "she is"), (r"\bit's\b", "it is"),
        (r"\bwe're\b", "we are"), (r"\bwe've\b", "we have"), (r"\bwe'd\b", "we would"), (r"\bwe'll\b", "we will"),
        (r"\bthey're\b", "they are"), (r"\bthey've\b", "they have"), (r"\bthey'd\b", "they would"), (r"\bthey'll\b", "they will"),
        (r"\bthat's\b", "that is"), (r"\bthere's\b", "there is"), (r"\bwhat's\b", "what is"),
        (r"\bwho's\b", "who is"), (r"\bwhere's\b", "where is"), (r"\bhow's\b", "how is"),
        (r"\bisn't\b", "is not"), (r"\baren't\b", "are not"), (r"\bwasn't\b", "was not"), (r"\bweren't\b", "were not"),
        (r"\bdon't\b", "do not"), (r"\bdoesn't\b", "does not"), (r"\bdidn't\b", "did not"),
        (r"\bhaven't\b", "have not"), (r"\bhasn't\b", "has not"), (r"\bhadn't\b", "had not"),
        (r"\bwouldn't\b", "would not"), (r"\bcouldn't\b", "could not"), (r"\bshouldn't\b", "should not"),
        (r"\blet's\b", "let us"),
    ]
    out = text
    for pat, repl in mapping:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


# ---------------------------------------------------------------- English sound -> Hangul (for names the model leaves in Latin)
_L = {"g": 0, "kk": 1, "n": 2, "d": 3, "r": 5, "l": 5, "m": 6, "b": 7, "v": 7, "s": 9, "z": 12, "j": 12, "ch": 14,
      "k": 15, "c": 15, "q": 15, "t": 16, "p": 17, "f": 17, "ph": 17, "h": 18, "th": 9, "sh": 9, "x": 15, "": 11}
_STANDALONE = {"s": "스", "t": "트", "d": "드", "ch": "치", "j": "지", "sh": "시", "z": "즈", "f": "프", "v": "브", "th": "스",
               "b": "브", "g": "그", "k": "크", "c": "크", "p": "프", "h": "흐", "r": "르", "x": "크스", "q": "크", "w": "우",
               "y": "이", "ph": "프", "l": "ㄹ", "m": "ㅁ", "n": "ㄴ", "ng": "ㅇ"}
_FINAL = {"n": 4, "m": 16, "l": 8, "ng": 21, "k": 1, "ck": 1, "p": 17, "r": 0}
_VOW = [("1", [0, 20]), ("ee", [20]), ("ea", [20]), ("oo", [13]), ("ou", [0, 13]), ("ow", [0, 13]), ("ai", [5, 20]), ("ay", [5, 20]),
        ("au", [8]), ("aw", [8]), ("oa", [8]), ("ie", [20]), ("ei", [5, 20]), ("ey", [5, 20]), ("oi", [8, 20]),
        ("oy", [8, 20]), ("ue", [13]), ("ui", [13, 20]), ("a", [0]), ("e", [5]), ("i", [20]), ("o", [8]), ("u", [13]), ("y", [20])]
_GLIDE_Y = {0: 2, 4: 6, 5: 7, 8: 12, 13: 17, 1: 3}
_GLIDE_W = {0: 9, 4: 14, 5: 15, 20: 16, 1: 10, 8: 14}
_VOWELS = set("aeiou1")


def _syl(l, v, t=0):
    return chr(0xAC00 + (l * 21 + v) * 28 + t)


def hangulize_word(word):
    w = word.lower().replace("'", "")
    if not w:
        return word
    w = re.sub(r"c(?=[eiy])", "s", w)
    if len(w) > 3 and w.endswith("e") and w[-2] not in _VOWELS:
        if w[-3] in _VOWELS and w[-4] not in _VOWELS:            # magic e: game -> geim, time -> taim
            w = w[:-3] + {"a": "ei", "i": "1", "o": "o", "u": "u", "e": "i"}[w[-3]] + w[-2]
        else:
            w = w[:-1]
    if len(w) > 2 and w.endswith("h") and w[-2] in _VOWELS:
        w = w[:-1]                                              # Sarah -> Sara
    units, i = [], 0
    while i < len(w):                                           # split into ('c', cons) / ('v', [vowels])
        ch = w[i]
        if ch in _VOWELS or (ch == "y" and i > 0 and (i + 1 >= len(w) or w[i + 1] not in _VOWELS)):
            for k, vs in _VOW:
                if w.startswith(k, i):
                    units.append(("v", list(vs))); i += len(k); break
            continue
        for k in ("ch", "sh", "th", "ph", "ck", "ng", "kk"):
            if w.startswith(k, i):
                units.append(("c", k)); i += 2; break
        else:
            if i + 1 < len(w) and w[i + 1] == ch:               # double letters sound once
                i += 1
            units.append(("c", ch)); i += 1
    out = []
    j = 0
    while j < len(units):
        kind, val = units[j]
        if kind == "v":
            for v in val:
                out.append([11, v, 0])
            j += 1; continue
        nxt = units[j + 1] if j + 1 < len(units) else None
        if nxt and nxt[0] == "v":
            vs = list(nxt[1]); lead = val
            if lead in ("y", "w"):
                table = _GLIDE_Y if lead == "y" else _GLIDE_W
                vs[0] = table.get(vs[0], vs[0] if lead == "y" else 13)
                L = 11
            elif lead == "sh":
                vs[0] = _GLIDE_Y.get(vs[0], vs[0]); L = 9
            elif lead == "x":
                out.append("크"); L = 9
            elif lead == "ck":
                L = 15
            elif lead == "ng":
                if out and isinstance(out[-1], list) and out[-1][2] == 0:
                    out[-1][2] = 21
                L = 0
            else:
                L = _L.get(lead, 11)
            out.append([L, vs[0], 0])
            for v in vs[1:]:
                out.append([11, v, 0])
            j += 2; continue
        # consonant not followed by a vowel
        prev = out[-1] if out and isinstance(out[-1], list) else None
        if val == "r":
            j += 1; continue                                     # non-rhotic r after a vowel
        if prev and prev[2] == 0 and val in _FINAL and (nxt is None or val in ("n", "m", "ng", "l")):
            prev[2] = _FINAL[val]
        else:
            out.append(_STANDALONE.get(val, ""))
        j += 1
    s = "".join(x if isinstance(x, str) else _syl(*x) for x in out)
    return s or word


def _replace_latin_token(m):
    """Translate known English leftovers via glossary; phonetic only for name-like tokens."""
    tok = m.group(0)
    low = tok.lower()
    if low in GLOSSARY:
        return GLOSSARY[low]
    if low in COMMON_ENGLISH or len(low) <= 2:
        # Tiny / common English fragment: drop phonetic junk; keep empty (Hangul around it is enough)
        # Prefer glossary again after stripping trailing 's
        base = low[:-2] if low.endswith("'s") else low
        if base in GLOSSARY:
            return GLOSSARY[base]
        return ""  # never emit i트스 / 트스 leftovers
    # Name-like (capitalized or unknown longer token): phonetic Hangulization
    return hangulize_word(tok)


def hangulize_leftovers(text):
    """Turn leftover Latin into Hangul. Common English/contractions use glossary; names use sound (Teo -> 테오)."""
    out = LATIN_WORD_RE.sub(_replace_latin_token, text)
    # Collapse spaces left by dropped tiny fragments
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +([,.!?])", r"\1", out)
    return out.strip() if out.strip() else text


# ---------------------------------------------------------------- engines
class OfflineEngine:
    name = "Built-in (offline)"

    def __init__(self, model_dir=None):
        self.model_dir = model_dir or res("model", "en_ko")
        self._tr = self._sp = None
        self._lock = threading.Lock()
        self.error = None

    def available(self):
        return os.path.isfile(os.path.join(self.model_dir, "model.bin"))

    def load(self):
        with self._lock:
            if self._tr is None and self.error is None:
                try:
                    import ctranslate2, sentencepiece as spm
                    self._sp = spm.SentencePieceProcessor(model_file=os.path.join(self.model_dir, "sentencepiece.model"))
                    threads = max(1, min(4, (os.cpu_count() or 2) // 2))
                    self._tr = ctranslate2.Translator(self.model_dir, device="cpu", inter_threads=1, intra_threads=threads)
                except Exception as e:                           # keep the app usable; status bar explains
                    self.error = "%s: %s" % (type(e).__name__, e)
        return self._tr is not None

    def translate(self, text):
        if not self.load():
            raise RuntimeError(self.error or "built-in model missing")
        sents = [s for s in split_sentences(text) if s.strip()]
        if not sents:
            return text
        toks = [self._sp.encode(s, out_type=str) for s in sents]
        with self._lock:
            res_ = self._tr.translate_batch(toks, beam_size=3, max_decoding_length=256, repetition_penalty=1.15)
        outs = [self._sp.decode(r.hypotheses[0]) for r in res_]
        return " ".join(o.strip() for o in outs)


class OnlineEngine:
    name = "Online"
    UA = "HANGUL WOOD/1.0.2 (EX Inc.)"

    def __init__(self):
        self.ctx = _ssl_ctx()

    def _get(self, url, timeout=5):
        req = urllib.request.Request(url, headers={"User-Agent": self.UA})
        with urllib.request.urlopen(req, timeout=timeout, context=self.ctx) as r:
            return r.read().decode("utf-8", "replace")

    def translate(self, text):
        q = urllib.parse.quote(text)
        errs = []
        try:
            data = json.loads(self._get("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q=" + q))
            out = "".join(part[0] for part in data[0] if part and part[0])
            if HANGUL_RE.search(out):
                return out
            errs.append("no Hangul in reply")
        except Exception as e:
            errs.append(type(e).__name__)
        try:
            data = json.loads(self._get("https://api.mymemory.translated.net/get?langpair=en%7Cko&q=" + q))
            out = (data.get("responseData") or {}).get("translatedText") or ""
            if HANGUL_RE.search(out) and "MYMEMORY WARNING" not in out.upper():
                return out
            errs.append("no Hangul in reply")
        except Exception as e:
            errs.append(type(e).__name__)
        raise RuntimeError("online translation unavailable (%s)" % ", ".join(errs))


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out = []
    for p in parts:                                              # keep very long runs digestible
        while len(p) > 400:
            cut = p.rfind(",", 0, 400)
            cut = cut if cut > 50 else 400
            out.append(p[:cut + 1]); p = p[cut + 1:].strip()
        out.append(p)
    return out


class Translator:
    """Mode: 'auto' (online first for long text, built-in backup; short = glossary/offline),
    'offline', 'online'. Thread-safe, cached."""

    def __init__(self, mode="auto", hangulize=True):
        self.mode, self.hangulize = mode, hangulize
        self.offline, self.online = OfflineEngine(), OnlineEngine()
        self.cache = OrderedDict()
        self._online_down_until = 0.0
        self.last_engine = ""
        self._clock = threading.Lock()

    def translate(self, text):
        """Returns (hangul, engine_name). Raises only if every allowed engine failed."""
        src = text.strip()
        if not src:
            return text, ""
        key = (self.mode, self.hangulize, src)
        with self._clock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key], self.last_engine or "cache"

        # 1) Glossary first — short words/phrases never hit context-free online MT
        gloss = glossary_lookup(src)
        if gloss is not None:
            self.last_engine = "Glossary"
            with self._clock:
                self.cache[key] = gloss
                while len(self.cache) > 800:
                    self.cache.popitem(last=False)
            return gloss, self.last_engine

        # 2) Exact translation of the whole text as typed.
        #    Auto / Online: full-text online translation first (keeps every word and its context),
        #    built-in model only as the offline backup. No word-by-word glossary joins.
        out, eng, err = None, "", None
        short = is_short_input(src)
        online_ok = self.mode == "online" or (self.mode == "auto" and time.time() >= self._online_down_until)
        if online_ok:
            try:
                out, eng = self.online.translate(src), self.online.name
            except Exception as e:
                err = e
                if self.mode == "auto":
                    self._online_down_until = time.time() + 30
        if out is None and self.mode in ("auto", "offline"):
            try:
                out, eng = self.offline.translate(expand_contractions_for_mt(src)), self.offline.name
            except Exception as e:
                err = e

        # 3) Last resort for a single unknown short token: phonetic name Hangulization
        if out is None and short and self.hangulize and word_count(src) == 1:
            tok = LATIN_WORD_RE.findall(src)
            if tok and tok[0].lower() not in COMMON_ENGLISH:
                out, eng = hangulize_word(tok[0]), "Phonetic"
            elif tok and tok[0].lower() in GLOSSARY:
                out, eng = GLOSSARY[tok[0].lower()], "Glossary"

        if out is None:
            raise RuntimeError(str(err) if err else "no engine")
        out = out.strip()
        if self.hangulize:
            out = hangulize_leftovers(out)
        # Guard: never leave tiny Latin fragments next to Hangul (the old i트스 bug)
        if HANGUL_RE.search(out):
            out = TINY_LATIN_RE.sub(
                lambda m: GLOSSARY.get(m.group(1).lower(), "") if m.group(1).lower() in COMMON_ENGLISH or len(m.group(1)) <= 2
                else hangulize_word(m.group(1)),
                out,
            )
            out = re.sub(r"[ \t]{2,}", " ", out).strip()
        self.last_engine = eng
        with self._clock:
            self.cache[key] = out
            while len(self.cache) > 800:
                self.cache.popitem(last=False)
        return out, eng


if __name__ == "__main__":
    t = Translator(mode=sys.argv[1] if len(sys.argv) > 1 else "offline")
    for s in ["Hello, my name is Teo and I make games.", "I love writing documents on rainy days."]:
        print(t.translate(s))
    for w in ["Teo", "London", "Sarah", "Michael", "game", "Chris", "Jennifer", "Hyperion"]:
        print(w, hangulize_word(w))
