"""HANGUL WOOD translation engine: English in, Hangul out.
Offline: built-in English->Korean neural model (CTranslate2 + SentencePiece), always available.
Online (optional, Auto mode): HTTPS translation for higher quality; falls back to the built-in model on any failure.
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import json, os, re, ssl, sys, threading, time, urllib.parse, urllib.request
from collections import OrderedDict

HANGUL_RE = re.compile(r"[\uac00-\ud7a3\u3131-\u318e]")
LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


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


def hangulize_leftovers(text):
    """Turn any English words still in Latin letters into Hangul by sound (Teo -> 테오)."""
    return LATIN_WORD_RE.sub(lambda m: hangulize_word(m.group(0)), text)


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
    UA = "HANGUL WOOD/1.0 (EX Inc.)"

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
    """Mode: 'auto' (online first, built-in backup), 'offline', 'online'. Thread-safe, cached."""

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
        out, eng, err = None, "", None
        if self.mode in ("auto", "online") and (self.mode == "online" or time.time() >= self._online_down_until):
            try:
                out, eng = self.online.translate(src), self.online.name
            except Exception as e:
                err = e
                self._online_down_until = time.time() + 60          # don't stall typing on a dead network
        if out is None and self.mode in ("auto", "offline"):
            try:
                out, eng = self.offline.translate(src), self.offline.name
            except Exception as e:
                err = e
        if out is None:
            raise RuntimeError(str(err) if err else "no engine")
        out = out.strip()
        if self.hangulize:
            out = hangulize_leftovers(out)
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
