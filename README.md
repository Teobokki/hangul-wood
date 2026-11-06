# HANGUL WOOD 1.0.0

![HANGUL WOOD](branding/hangul-wood-logo.jpg)

**HANGUL WOOD** is a document editor for Windows: you type in English and your page fills with Korean **Hangul**.

- **Live Hangul**: write English straight onto the page. When you finish a sentence (`.` `!` `?`), press Enter, or pause, the English turns into Hangul in place, keeping your formatting. Ctrl+Z brings the English back.
- **Convert now** (Ctrl+Space) for the current paragraph or a selection, or **Whole document**.
- Hover any Hangul to see the English it came from; the **English → 한글** pane lists everything you typed.
- Ribbon tabs: **Home** (clipboard, font, size, bold/italic/underline/strike, sub/superscript, colors, lists, indents, alignment, line spacing, styles), **Insert** (page break, table, picture, line, date), **Layout** (margins, A4/Letter), **Hangul** (live mode, translator, names), **View** (ruler, English pane).
- Files: `.hwd` (HANGUL WOOD document), `.txt`, open `.html`; Export PDF, Export web page, Print.

## Translation
- **Built-in (offline)**: an English→Korean neural model ships inside the app (Argos Translate en→ko, OPUS data, run with CTranslate2 + SentencePiece). Works with no internet; nothing leaves your PC.
- **Auto** (default): tries an online translator over HTTPS (certificate checks on) for higher quality, and falls back to the built-in model instantly if the network is down.
- **Online only** is also available.
- English names the translator leaves in Latin letters are written in Hangul by sound (Teo → 테오); switch this off on the Hangul tab.
- If translation fails, your English stays on the page and the status bar says why.

## Install
Download `HANGUL-WOOD-Setup-1.0.0.exe` from [Releases](https://github.com/Teobokki/hangul-wood/releases/latest). Per-user install, no admin needed. Or unzip the portable build and run `HANGUL WOOD.exe`.

## Credits
Font: Noto Sans KR (SIL Open Font License, `fonts/OFL.txt`). Built-in model: Argos Translate en_ko 1.1 (see `model/en_ko/MODEL_README.md`).

©2026 EX Inc./HYPERION DIGITAL ©2026
