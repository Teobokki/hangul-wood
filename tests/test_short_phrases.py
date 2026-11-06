"""No-network self-test for HANGUL WOOD short-phrase glossary / contraction handling."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hw_translate as hwt


CASES = [
    ("it's", "그건"),
    ("hi", "안녕"),
    ("hello", "안녕하세요"),
    ("thanks", "고마워"),
    ("sorry", "미안"),
    ("hood", "후드"),
    ("hoodie", "후드티"),
    ("I'm", "나는"),
    ("don't", "하지 마"),
    ("that's", "그건"),
]


class ShortPhraseTests(unittest.TestCase):
    def test_glossary_exact(self):
        for eng, ko in CASES:
            with self.subTest(eng=eng):
                out, eng_name = hwt.Translator(mode="offline", hangulize=True).translate(eng)
                self.assertEqual(out, ko, "%r -> %r (via %s), want %r" % (eng, out, eng_name, ko))
                self.assertEqual(eng_name, "Glossary")

    def test_its_never_latin_junk(self):
        out, _ = hwt.Translator(mode="offline", hangulize=True).translate("it's")
        self.assertNotIn("트스", out)
        self.assertFalse(any(c.isascii() and c.isalpha() for c in out), out)

    def test_hangulize_skips_common_english(self):
        # leftover "it's" must not become 이트스
        self.assertEqual(hwt.hangulize_leftovers("it's"), "그건")
        self.assertEqual(hwt.hangulize_leftovers("hood"), "후드")
        # names still phonetic
        self.assertTrue(hwt.HANGUL_RE.search(hwt.hangulize_word("Teo")))

    def test_short_skips_online_when_glossary_hits(self):
        # Even in online-only mode, glossary wins first (no network needed)
        out, eng = hwt.Translator(mode="online", hangulize=True).translate("hood")
        self.assertEqual(out, "후드")
        self.assertEqual(eng, "Glossary")

    def test_is_short_and_sentence_gates(self):
        self.assertTrue(hwt.is_short_input("hi"))
        self.assertTrue(hwt.is_short_input("hood"))
        self.assertTrue(hwt.is_short_input("thank you"))
        self.assertFalse(hwt.looks_like_sentence("hood"))
        self.assertFalse(hwt.looks_like_sentence("it's"))
        self.assertTrue(hwt.looks_like_sentence("Hello, my name is Teo and I make games."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
