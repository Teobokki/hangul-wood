"""HANGUL WOOD - a document editor where you type English and the page fills with Hangul.
©2026 EX Inc./HYPERION DIGITAL ©2026"""
import json, os, queue, re, sys, textwrap, threading
from datetime import date

APP_NAME = "HANGUL WOOD"
APP_VERSION = "1.0.3"
COPYRIGHT = "\u00a92026 EX Inc./HYPERION DIGITAL \u00a92026"

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EXInc.HangulWood")
    except Exception:
        pass

from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSize, QSizeF, QSettings, QPointF, QRectF, QMarginsF, QBuffer, QByteArray, QIODevice, QEvent
from PySide6.QtGui import (QIcon, QPixmap, QFont, QFontDatabase, QColor, QPainter, QPen, QBrush, QPainterPath, QTextCharFormat,
                           QTextCursor, QTextBlockFormat, QTextListFormat, QTextTableFormat, QTextFormat, QTextDocument, QAction,
                           QKeySequence, QImage, QPageSize, QPageLayout, QPdfWriter, QActionGroup, QTextLength, QGuiApplication)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QToolButton,
                               QPushButton, QFrame, QTextEdit, QScrollArea, QFontComboBox, QComboBox, QColorDialog, QFileDialog,
                               QMessageBox, QStackedWidget, QDockWidget, QListWidget, QListWidgetItem, QMenu, QSizePolicy,
                               QButtonGroup, QDialog, QToolTip, QStatusBar)
import hw_translate as hwt
from hw_icons import make_icon
import hw_icons

NAVY, NAVY2, GREEN, GREEN2 = "#0f2e57", "#173c6d", "#8cbf3f", "#6fa22a"
INK, MUTED, LINE, RIBBON, CANVAS = "#1d2733", "#5e6b7a", "#d5dbe3", "#f6f8fa", "#e3e8ee"
DONE = QTextFormat.UserProperty + 1          # char was produced by HANGUL WOOD (Hangul output)
SRC = QTextFormat.UserProperty + 2           # the English it came from (shown as a tooltip)
PAGES = {"A4": (794, 1123), "Letter": (816, 1056)}
MARGINS = {"Narrow": 48, "Normal": 96, "Wide": 144}
res = hwt.res
KFONT = "Noto Sans KR"


# ------------------------------------------------------------------------------------------------ translation worker
class Worker(QObject):
    done = Signal(int, str, str, str)       # job id, source, hangul, engine
    failed = Signal(int, str, str)          # job id, source, error
    ready = Signal(str)

    def __init__(self, tr):
        super().__init__()
        self.tr, self.q = tr, queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def submit(self, jid, text):
        self.q.put((jid, text))

    def _run(self):
        ok = self.tr.offline.load() if self.tr.mode != "online" else True
        self.ready.emit("" if ok else (self.tr.offline.error or "built-in model missing"))
        while True:
            jid, text = self.q.get()
            try:
                out, eng = self.tr.translate(text)
                self.done.emit(jid, text, out, eng)
            except Exception as e:
                self.failed.emit(jid, text, str(e))


# ------------------------------------------------------------------------------------------------ page + ruler
class Page(QTextEdit):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.page_h = 1123
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.document().documentLayout().documentSizeChanged.connect(self.fit)
        self.setStyleSheet("QTextEdit{background:white; color:#111; selection-background-color:#bcd7a0; selection-color:#111;}")

    def fit(self, *_):
        h = int(self.document().size().height()) + 4
        pages = max(1, -(-h // self.page_h))
        if self.height() != pages * self.page_h:
            self.setFixedHeight(pages * self.page_h)
        self.win.update_status()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self.viewport())
        p.setPen(QPen(QColor("#c9d2dc"), 1, Qt.DashLine))
        y = self.page_h
        while y < self.height():
            p.drawLine(0, y, self.width(), y); y += self.page_h
        p.end()

    def viewportEvent(self, e):
        if e.type() == QEvent.ToolTip:
            src = self.cursorForPosition(e.pos()).charFormat().property(SRC)
            if src:
                QToolTip.showText(e.globalPos(), "English: " + str(src), self)
            else:
                QToolTip.hideText()
            return True
        return super().viewportEvent(e)

    def insertFromMimeData(self, md):
        if md.hasImage() and not md.hasText():
            self.win.insert_image_obj(QImage(md.imageData())); return
        super().insertFromMimeData(md)

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        self.win.ensure_cursor_visible()


class Ruler(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win; self.setFixedHeight(22)

    def paintEvent(self, e):
        p = QPainter(self); p.fillRect(self.rect(), QColor(CANVAS))
        pw = self.win.page.width()
        x0 = self.win.sheet.mapTo(self.win, self.win.sheet.rect().topLeft()).x() - self.mapTo(self.win, self.rect().topLeft()).x()
        m = int(self.win.page.document().documentMargin())
        p.fillRect(x0, 3, pw, 16, QColor("#d7dee6")); p.fillRect(x0 + m, 3, pw - 2 * m, 16, QColor("white"))
        p.setPen(QColor(MUTED)); f = QFont(KFONT); f.setPixelSize(9); p.setFont(f)
        q = 96 / 2.54 / 4
        i = 1
        while x0 + m + i * q <= x0 + pw - 4:
            x = x0 + m + i * q
            if i % 4 == 0:
                p.drawText(QRectF(x - 10, 4, 20, 14), Qt.AlignCenter, str(i // 4))
            elif i % 2 == 0:
                p.drawLine(QPointF(x, 8), QPointF(x, 14))
            else:
                p.drawLine(QPointF(x, 10), QPointF(x, 12))
            i += 1
        p.setBrush(QColor(GREEN)); p.setPen(Qt.NoPen)
        for xx in (x0 + m, x0 + pw - m):
            p.drawPolygon([QPointF(xx - 5, 19), QPointF(xx + 5, 19), QPointF(xx, 13)])
        p.end()


# ------------------------------------------------------------------------------------------------ ribbon helpers
def tool(icon, text, tip, slot=None, big=False, checkable=False):
    b = QToolButton(); b.setIcon(icon); b.setToolTip(tip); b.setText(text); b.setCheckable(checkable); b.setAutoRaise(True)
    if big:
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon); b.setIconSize(QSize(30, 30)); b.setMinimumWidth(60)
    else:
        b.setToolButtonStyle(Qt.ToolButtonIconOnly if text == "" else Qt.ToolButtonTextBesideIcon); b.setIconSize(QSize(18, 18))
    if slot:
        (b.toggled if checkable else b.clicked).connect(slot)
    return b


def text_tool(label, tip, slot, font=None, checkable=False):
    b = QToolButton(); b.setText(label); b.setToolTip(tip); b.setAutoRaise(True); b.setCheckable(checkable); b.setFixedSize(28, 26)
    if font: b.setFont(font)
    (b.toggled if checkable else b.clicked).connect(slot)
    return b


class Group(QFrame):
    def __init__(self, title):
        super().__init__(); self.setObjectName("group")
        v = QVBoxLayout(self); v.setContentsMargins(8, 4, 8, 2); v.setSpacing(2)
        self.body = QWidget(); self.grid = QGridLayout(self.body); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(2)
        v.addWidget(self.body, 1)
        cap = QLabel(title); cap.setAlignment(Qt.AlignCenter); cap.setObjectName("cap"); v.addWidget(cap)


def ribbon_page(groups):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(6, 4, 6, 2); h.setSpacing(0)
    for g in groups:
        h.addWidget(g)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine); sep.setObjectName("gsep"); h.addWidget(sep)
    h.addStretch(1)
    return w


# ------------------------------------------------------------------------------------------------ main window
class Main(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.settings = QSettings("EX Inc", "HANGUL WOOD")
        self.path, self.untitled_n = None, 1
        self.page_name = self.settings.value("page", "A4")
        self.margin_name = self.settings.value("margin", "Normal")
        self.tr = hwt.Translator(mode=self.settings.value("engine", "auto"),
                                 hangulize=self.settings.value("hangulize", "true") == "true")
        self.live = self.settings.value("live", "true") == "true"
        self.jobs, self.next_id, self.applying = {}, 1, False
        self.engine_note = "Loading the built-in translator\u2026"
        self.worker = Worker(self.tr)
        self.worker.done.connect(self.on_done); self.worker.failed.connect(self.on_failed); self.worker.ready.connect(self.on_ready)
        self.setWindowIcon(QIcon(res("assets", "logo.ico")))
        self.resize(1360, 900)
        # pause: finished sentences right away; an unfinished line only after a long pause,
        # so a sentence is never translated in pieces (pieces lose meaning)
        self.idle = QTimer(self, singleShot=True, interval=1800, timeout=lambda: (self.convert_pending(True), self.idle_long.start()))
        self.idle_long = QTimer(self, singleShot=True, interval=4500, timeout=lambda: self.convert_pending(False))
        self.soon = QTimer(self, singleShot=True, interval=250, timeout=lambda: self.convert_pending(True))
        self.hl = QTimer(self, singleShot=True, interval=120, timeout=self.highlight_pending)
        self.build()
        if path:
            self.load(path)
        else:
            self.new_doc(ask=False)

    # ---------- UI
    def build(self):
        root = QWidget(); self.setCentralWidget(root)
        v = QVBoxLayout(root); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)

        band = QFrame(); band.setObjectName("band"); band.setFixedHeight(40)
        hb = QHBoxLayout(band); hb.setContentsMargins(10, 0, 10, 0); hb.setSpacing(4)
        logo = QLabel(); logo.setPixmap(QPixmap(res("assets", "icon256.png")).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        hb.addWidget(logo); hb.addSpacing(6)
        for kind, tip, slot in (("save", "Save (Ctrl+S)", self.save), ("undo", "Undo (Ctrl+Z)", lambda: self.page.undo()),
                                ("redo", "Redo (Ctrl+Y)", lambda: self.page.redo())):
            b = tool(make_icon(kind, "white"), "", tip, slot); b.setObjectName("qa"); hb.addWidget(b)
        hb.addStretch(1)
        self.title_lbl = QLabel(); self.title_lbl.setObjectName("title"); hb.addWidget(self.title_lbl)
        hb.addStretch(1)
        self.live_pill = QPushButton(); self.live_pill.setObjectName("pill"); self.live_pill.setCheckable(True)
        self.live_pill.toggled.connect(self.set_live); self.live_pill.setCursor(Qt.PointingHandCursor)
        hb.addWidget(self.live_pill)
        v.addWidget(band)

        strip = QFrame(); strip.setObjectName("strip"); strip.setFixedHeight(34)
        hs = QHBoxLayout(strip); hs.setContentsMargins(6, 0, 6, 0); hs.setSpacing(2)
        filebtn = QToolButton(); filebtn.setText("File"); filebtn.setObjectName("filebtn"); filebtn.setPopupMode(QToolButton.InstantPopup)
        filebtn.setMenu(self.file_menu()); hs.addWidget(filebtn); hs.addSpacing(4)
        self.tabs = QButtonGroup(self); self.tabs.setExclusive(True)
        self.stack = QStackedWidget(); self.stack.setObjectName("ribbon"); self.stack.setFixedHeight(104)
        self.log = QListWidget(); self.log.setObjectName("log"); self.log.setWordWrap(True)
        self.ruler = Ruler(self); self.page = Page(self)
        for i, (name, page) in enumerate((("Home", self.home_tab()), ("Insert", self.insert_tab()), ("Layout", self.layout_tab()),
                                          ("Hangul", self.hangul_tab()), ("View", self.view_tab()))):
            b = QPushButton(name); b.setCheckable(True); b.setObjectName("tab"); b.setCursor(Qt.PointingHandCursor)
            self.tabs.addButton(b, i); hs.addWidget(b); self.stack.addWidget(page)
        self.tabs.idClicked.connect(self.stack.setCurrentIndex); self.tabs.button(0).setChecked(True)
        hs.addStretch(1)
        hint = QLabel("Type English \u2192 \ud55c\uae00 appears on the page"); hint.setObjectName("hint"); hs.addWidget(hint)
        v.addWidget(strip); v.addWidget(self.stack)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet("background:%s" % LINE); v.addWidget(line)

        v.addWidget(self.ruler)
        self.scroll = QScrollArea(); self.scroll.setObjectName("canvas"); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame)
        holder = QWidget(); holder.setObjectName("canvasw"); hl = QVBoxLayout(holder); hl.setContentsMargins(0, 26, 0, 40)
        row = QHBoxLayout(); row.addStretch(1)
        self.sheet = QFrame(); self.sheet.setObjectName("sheet"); sl = QVBoxLayout(self.sheet); sl.setContentsMargins(0, 0, 0, 0); sl.addWidget(self.page)
        row.addWidget(self.sheet); row.addStretch(1); hl.addLayout(row); hl.addStretch(1)
        self.scroll.setWidget(holder); v.addWidget(self.scroll, 1)
        self.scroll.horizontalScrollBar().valueChanged.connect(lambda *_: self.ruler.update())
        self.ruler.setVisible(self.settings.value("ruler", "true") == "true")

        self.dock = QDockWidget("English \u2192 \ud55c\uae00", self); self.dock.setWidget(self.log); self.dock.setObjectName("dock")
        self.dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock); self.dock.setMinimumWidth(280)
        self.dock.setVisible(self.settings.value("log", "true") == "true")
        self.dock.visibilityChanged.connect(lambda vis: (self.log_btn.blockSignals(True), self.log_btn.setChecked(vis), self.log_btn.blockSignals(False)))

        sb = QStatusBar(); self.setStatusBar(sb)
        self.st_page, self.st_words, self.st_lang = QLabel(), QLabel(), QLabel("English \u2192 \ud55c\uad6d\uc5b4")
        for w in (self.st_page, self.st_words, self.st_lang):
            w.setContentsMargins(8, 0, 8, 0); sb.addWidget(w)
        self.st_engine = QLabel(); sb.addPermanentWidget(self.st_engine)
        self.st_live = QLabel(); sb.addPermanentWidget(self.st_live)

        self.page.textChanged.connect(self.update_status)
        self.page.document().contentsChange.connect(self.on_change)
        self.page.cursorPositionChanged.connect(self.on_cursor)
        self.page.currentCharFormatChanged.connect(self.sync_format)
        self.page.document().modificationChanged.connect(lambda *_: self.update_title())
        self.apply_page()
        self.shortcuts()
        self.set_live(self.live)
        self.setStyleSheet(STYLE)

    def file_menu(self):
        m = QMenu(self)
        for kind, text, key, slot in (("new", "New", QKeySequence.New, lambda: self.new_doc()),
                                      ("open", "Open\u2026", QKeySequence.Open, self.open_doc),
                                      ("save", "Save", QKeySequence.Save, self.save),
                                      (None, "Save As\u2026", QKeySequence("Ctrl+Shift+S"), self.save_as), (None, None, None, None),
                                      ("pdf", "Export PDF\u2026", None, self.export_pdf),
                                      (None, "Export Web Page (.html)\u2026", None, self.export_html),
                                      ("print", "Print\u2026", QKeySequence.Print, self.print_doc), (None, None, None, None),
                                      (None, "About HANGUL WOOD", None, self.about), (None, "Exit", None, self.close)):
            if text is None:
                m.addSeparator(); continue
            a = m.addAction(make_icon(kind) if kind else QIcon(), text, slot)
            if key:
                a.setShortcut(key); self.addAction(a)
        return m

    def home_tab(self):
        clip = Group("Clipboard")
        clip.grid.addWidget(tool(make_icon("paste"), "Paste", "Paste (Ctrl+V)", lambda: self.page.paste(), big=True), 0, 0, 2, 1)
        clip.grid.addWidget(tool(make_icon("cut"), "Cut", "Cut (Ctrl+X)", lambda: self.page.cut()), 0, 1)
        clip.grid.addWidget(tool(make_icon("copy"), "Copy", "Copy (Ctrl+C)", lambda: self.page.copy()), 1, 1)

        font = Group("Font")
        self.font_box = QFontComboBox(); self.font_box.setWritingSystem(QFontDatabase.Korean); self.font_box.setFixedWidth(170)
        self.font_box.currentFontChanged.connect(lambda f: self.merge(family=f.family()))
        self.size_box = QComboBox(); self.size_box.setEditable(True); self.size_box.setFixedWidth(60)
        self.size_box.addItems(["%g" % s for s in SIZES])
        self.size_box.textActivated.connect(lambda t: self.merge(size=t))
        r0 = QHBoxLayout(); r0.setSpacing(3); r0.addWidget(self.font_box); r0.addWidget(self.size_box)
        r0.addWidget(text_tool("A\u207a", "Grow font", lambda: self.step_size(+1)))
        r0.addWidget(text_tool("A\u207b", "Shrink font", lambda: self.step_size(-1)))
        r0.addWidget(tool(make_icon("clear"), "", "Clear formatting", self.clear_format))
        bf, itf, uf, sf = QFont("Georgia", 11, QFont.Bold), QFont("Georgia", 11), QFont("Georgia", 11), QFont("Georgia", 11)
        itf.setItalic(True); uf.setUnderline(True); sf.setStrikeOut(True)
        self.b_bold = text_tool("B", "Bold (Ctrl+B)", lambda on: self.merge(bold=on), bf, True)
        self.b_ital = text_tool("I", "Italic (Ctrl+I)", lambda on: self.merge(italic=on), itf, True)
        self.b_under = text_tool("U", "Underline (Ctrl+U)", lambda on: self.merge(underline=on), uf, True)
        self.b_strike = text_tool("ab", "Strikethrough", lambda on: self.merge(strike=on), sf, True)
        self.b_sub = text_tool("x\u2082", "Subscript", lambda on: self.merge(valign="sub" if on else "normal"), None, True)
        self.b_sup = text_tool("x\u00b2", "Superscript", lambda on: self.merge(valign="sup" if on else "normal"), None, True)
        r1 = QHBoxLayout(); r1.setSpacing(1)
        for b in (self.b_bold, self.b_ital, self.b_under, self.b_strike, self.b_sub, self.b_sup):
            r1.addWidget(b)
        r1.addSpacing(6)
        r1.addWidget(tool(make_icon("highlight"), "", "Highlight color", lambda: self.pick_color(bg=True)))
        r1.addWidget(tool(make_icon("color"), "", "Font color", lambda: self.pick_color())); r1.addStretch(1)
        font.grid.addLayout(r0, 0, 0); font.grid.addLayout(r1, 1, 0)

        para = Group("Paragraph")
        r0 = QHBoxLayout(); r0.setSpacing(1)
        r0.addWidget(tool(make_icon("bullets"), "", "Bullets", lambda: self.toggle_list(QTextListFormat.ListDisc)))
        r0.addWidget(tool(make_icon("numbers"), "", "Numbering", lambda: self.toggle_list(QTextListFormat.ListDecimal)))
        r0.addWidget(tool(make_icon("outdent"), "", "Decrease indent", lambda: self.indent(-1)))
        r0.addWidget(tool(make_icon("indent"), "", "Increase indent", lambda: self.indent(+1)))
        sp = tool(make_icon("spacing"), "", "Line spacing"); sp.setPopupMode(QToolButton.InstantPopup)
        sm = QMenu(sp)
        for val in (100, 115, 150, 200, 250, 300):
            sm.addAction("%.2f" % (val / 100.0), lambda v=val: self.line_spacing(v))
        sp.setMenu(sm); r0.addWidget(sp); r0.addStretch(1)
        r1 = QHBoxLayout(); r1.setSpacing(1); self.align_btns = {}
        for kind, al, tip in (("left", Qt.AlignLeft, "Align left (Ctrl+L)"), ("center", Qt.AlignHCenter, "Center (Ctrl+E)"),
                              ("right", Qt.AlignRight, "Align right (Ctrl+R)"), ("justify", Qt.AlignJustify, "Justify (Ctrl+J)")):
            b = tool(make_icon(kind), "", tip, lambda _=False, a=al: self.set_align(a)); b.setCheckable(True)
            self.align_btns[int(al.value if hasattr(al, "value") else al)] = b; r1.addWidget(b)
        r1.addStretch(1)
        para.grid.addLayout(r0, 0, 0); para.grid.addLayout(r1, 1, 0)

        styles = Group("Styles")
        sr = QHBoxLayout(); sr.setSpacing(4)
        for name, sample in (("Normal", "\uac00\ub098\ub2e4"), ("Title", "\uc81c\ubaa9"), ("Heading 1", "\uc81c\ubaa9 1"),
                             ("Heading 2", "\uc81c\ubaa9 2"), ("Quote", "\uc778\uc6a9")):
            b = QToolButton(); b.setObjectName("style"); b.setText("%s\n%s" % (sample, name)); b.setFixedSize(74, 60)
            b.clicked.connect(lambda _=False, n=name: self.apply_style(n)); sr.addWidget(b)
        styles.grid.addLayout(sr, 0, 0)

        hang = Group("Hangul")
        hang.grid.addWidget(tool(make_icon("convert"), "Convert\nnow", "Turn the English in this paragraph into Hangul (Ctrl+Space)", self.convert_now, big=True), 0, 0)
        self.live_btn_home = tool(make_icon("live"), "Live\nHangul", "Convert as you type: at . ! ? Enter or a short pause (Ctrl+Shift+H)", self.set_live, big=True, checkable=True)
        hang.grid.addWidget(self.live_btn_home, 0, 1)
        return ribbon_page([clip, font, para, styles, hang])

    def insert_tab(self):
        pages = Group("Pages")
        pages.grid.addWidget(tool(make_icon("pagebreak"), "Page\nbreak", "Start a new page (Ctrl+Enter)", self.page_break, big=True), 0, 0)
        tables = Group("Tables")
        tb = tool(make_icon("table"), "Table", "Insert a table", big=True); tb.setPopupMode(QToolButton.InstantPopup)
        tm = QMenu(tb)
        for r, c in ((2, 2), (3, 3), (4, 3), (5, 4), (8, 2)):
            tm.addAction("%d \u00d7 %d" % (r, c), lambda r=r, c=c: self.insert_table(r, c))
        tb.setMenu(tm); tables.grid.addWidget(tb, 0, 0)
        ill = Group("Illustrations")
        ill.grid.addWidget(tool(make_icon("picture"), "Picture", "Insert a picture from this PC", self.insert_picture, big=True), 0, 0)
        txt = Group("Text")
        txt.grid.addWidget(tool(make_icon("hline"), "Line", "Horizontal line", self.insert_hline, big=True), 0, 0)
        txt.grid.addWidget(tool(make_icon("date"), "Date", "Insert today's date in Korean", self.insert_date, big=True), 0, 1)
        return ribbon_page([pages, tables, ill, txt])

    def layout_tab(self):
        setup = Group("Page Setup")
        mb = tool(make_icon("margins"), "Margins", "Page margins", big=True); mb.setPopupMode(QToolButton.InstantPopup)
        mm = QMenu(mb)
        for n in MARGINS:
            mm.addAction("%s (%.1f cm)" % (n, MARGINS[n] / 96 * 2.54), lambda n=n: self.set_margin(n))
        mb.setMenu(mm)
        pb = tool(make_icon("pagesize"), "Size", "Paper size", big=True); pb.setPopupMode(QToolButton.InstantPopup)
        pm = QMenu(pb)
        for n in PAGES:
            pm.addAction(n, lambda n=n: self.set_page(n))
        pb.setMenu(pm)
        setup.grid.addWidget(mb, 0, 0); setup.grid.addWidget(pb, 0, 1)
        spg = Group("Line spacing")
        for i, (val, lab) in enumerate(((100, "1.0"), (150, "1.5"), (200, "2.0"))):
            b = QPushButton("Line " + lab); b.clicked.connect(lambda _=False, v=val: self.line_spacing(v)); spg.grid.addWidget(b, i, 0)
        return ribbon_page([setup, spg])

    def hangul_tab(self):
        conv = Group("Convert")
        self.live_btn = tool(make_icon("live"), "Live\nHangul", "Convert as you type", self.set_live, big=True, checkable=True)
        conv.grid.addWidget(self.live_btn, 0, 0)
        conv.grid.addWidget(tool(make_icon("convert"), "Convert\nnow", "Convert this paragraph or the selection (Ctrl+Space)", self.convert_now, big=True), 0, 1)
        conv.grid.addWidget(tool(make_icon("convertall"), "Whole\ndocument", "Convert every English passage in the document", self.convert_all, big=True), 0, 2)
        eng = Group("Translator")
        self.eng_group = QButtonGroup(self); self.eng_group.setExclusive(True)
        for i, (mode, label) in enumerate((("auto", "Auto: online, built-in backup"), ("offline", "Built-in only (works offline)"),
                                            ("online", "Online only"))):
            b = QPushButton(label); b.setCheckable(True); b.setObjectName("radio"); b.setChecked(self.tr.mode == mode)
            b.clicked.connect(lambda _=False, m=mode: self.set_engine(m)); self.eng_group.addButton(b); eng.grid.addWidget(b, i, 0)
        names = Group("Names")
        self.hz_btn = QPushButton("Write leftover English names\nin Hangul (Teo \u2192 \ud14c\uc624)"); self.hz_btn.setCheckable(True)
        self.hz_btn.setObjectName("radio"); self.hz_btn.setChecked(self.tr.hangulize); self.hz_btn.toggled.connect(self.set_hangulize)
        names.grid.addWidget(self.hz_btn, 0, 0)
        logg = Group("Show")
        self.log_btn = tool(make_icon("log"), "English\npane", "Show what you typed next to the Hangul", lambda on: hasattr(self, "dock") and self.dock.setVisible(on), big=True, checkable=True)
        self.log_btn.setChecked(self.settings.value("log", "true") == "true")
        logg.grid.addWidget(self.log_btn, 0, 0)
        return ribbon_page([conv, eng, names, logg])

    def view_tab(self):
        show = Group("Show")
        self.ruler_btn = tool(make_icon("ruler"), "Ruler", "Show the ruler", lambda on: self.ruler.setVisible(on), big=True, checkable=True)
        self.ruler_btn.setChecked(self.settings.value("ruler", "true") == "true")
        show.grid.addWidget(self.ruler_btn, 0, 0)
        show.grid.addWidget(tool(make_icon("log"), "English\npane", "Show / hide the English pane", lambda: self.dock.setVisible(not self.dock.isVisible()), big=True), 0, 1)
        return ribbon_page([show])

    def shortcuts(self):
        for key, slot in (("Ctrl+B", lambda: self.b_bold.click()), ("Ctrl+I", lambda: self.b_ital.click()), ("Ctrl+U", lambda: self.b_under.click()),
                          ("Ctrl+L", lambda: self.set_align(Qt.AlignLeft)), ("Ctrl+E", lambda: self.set_align(Qt.AlignHCenter)),
                          ("Ctrl+R", lambda: self.set_align(Qt.AlignRight)), ("Ctrl+J", lambda: self.set_align(Qt.AlignJustify)),
                          ("Ctrl+Space", self.convert_now), ("Ctrl+Return", self.page_break),
                          ("Ctrl+Shift+H", lambda: self.set_live(not self.live))):
            a = QAction(self); a.setShortcut(QKeySequence(key)); a.setShortcutContext(Qt.WindowShortcut); a.triggered.connect(slot); self.addAction(a)

    # ---------- page geometry
    def apply_page(self):
        w, h = PAGES.get(self.page_name, PAGES["A4"])
        self.page.page_h = h
        self.page.setFixedWidth(w); self.page.document().setDocumentMargin(MARGINS.get(self.margin_name, 96))
        self.page.fit(); self.ruler.update()

    def set_page(self, n):
        self.page_name = n; self.settings.setValue("page", n); self.apply_page()

    def set_margin(self, n):
        self.margin_name = n; self.settings.setValue("margin", n); self.apply_page()

    def ensure_cursor_visible(self):
        r = self.page.cursorRect()
        pt = self.page.viewport().mapTo(self.scroll.widget(), r.center())
        self.scroll.ensureVisible(pt.x(), pt.y(), 40, 80)

    def resizeEvent(self, e):
        super().resizeEvent(e); self.ruler.update()

    # ---------- formatting
    def merge(self, family=None, size=None, bold=None, italic=None, underline=None, strike=None, valign=None):
        f = QTextCharFormat()
        if family: f.setFontFamilies([family])
        if size:
            try: f.setFontPointSize(float(size))
            except ValueError: return
        if bold is not None: f.setFontWeight(QFont.Bold if bold else QFont.Normal)
        if italic is not None: f.setFontItalic(italic)
        if underline is not None: f.setFontUnderline(underline)
        if strike is not None: f.setFontStrikeOut(strike)
        if valign:
            f.setVerticalAlignment({"sup": QTextCharFormat.AlignSuperScript, "sub": QTextCharFormat.AlignSubScript}.get(valign, QTextCharFormat.AlignNormal))
        self.page.mergeCurrentCharFormat(f); self.page.setFocus()

    def step_size(self, d):
        cur = self.page.currentCharFormat().fontPointSize() or 12
        nxt = [s for s in SIZES if s > cur] if d > 0 else [s for s in SIZES if s < cur]
        if nxt: self.merge(size=nxt[0] if d > 0 else nxt[-1])

    def pick_color(self, bg=False):
        c = QColorDialog.getColor(QColor("#ffe25a" if bg else NAVY), self, "Highlight color" if bg else "Font color")
        if c.isValid():
            f = QTextCharFormat()
            if bg: f.setBackground(c)
            else: f.setForeground(c)
            self.page.mergeCurrentCharFormat(f)

    def clear_format(self):
        f = QTextCharFormat(); f.setFontFamilies([KFONT]); f.setFontPointSize(12); f.setFontWeight(QFont.Normal); f.setFontItalic(False)
        f.setFontUnderline(False); f.setFontStrikeOut(False); f.setForeground(QColor("#111111")); f.setBackground(Qt.transparent)
        f.setVerticalAlignment(QTextCharFormat.AlignNormal)
        self.page.mergeCurrentCharFormat(f)          # merge keeps the hidden English source tags

    def set_align(self, a):
        self.page.setAlignment(a); self.sync_format(self.page.currentCharFormat())

    def toggle_list(self, style):
        c = self.page.textCursor(); lst = c.currentList()
        c.beginEditBlock()
        if lst and lst.format().style() == style:
            for i in reversed(range(lst.count())):
                pass
            bf = c.blockFormat(); lst.remove(c.block()); bf.setIndent(0); c.setBlockFormat(bf)
        else:
            lf = QTextListFormat(); lf.setStyle(style); lf.setIndent(1); c.createList(lf)
        c.endEditBlock()

    def indent(self, d):
        c = self.page.textCursor(); lst = c.currentList()
        if lst:
            lf = lst.format(); lf.setIndent(max(1, lf.indent() + d)); lst.setFormat(lf); return
        bf = c.blockFormat(); bf.setIndent(max(0, bf.indent() + d)); c.setBlockFormat(bf)

    def line_spacing(self, pct):
        bf = QTextBlockFormat(); bf.setLineHeight(pct, 1)     # 1 = proportional
        self.page.textCursor().mergeBlockFormat(bf)

    def apply_style(self, name):
        size, bold, italic, level, color = {"Normal": (12, False, False, 0, "#111111"), "Title": (28, True, False, 0, NAVY),
                                            "Heading 1": (20, True, False, 1, NAVY), "Heading 2": (15, True, False, 2, GREEN2),
                                            "Quote": (13, False, True, 0, "#4a5868")}[name]
        c = self.page.textCursor(); c.beginEditBlock()
        bf = c.blockFormat(); bf.setHeadingLevel(level); bf.setLeftMargin(30 if name == "Quote" else 0)
        big = level or name == "Title"
        bf.setTopMargin(14 if big else 0); bf.setBottomMargin(8 if big else 0)
        bf.setAlignment(Qt.AlignHCenter if name == "Title" else Qt.AlignLeft)
        c.setBlockFormat(bf)
        sel = QTextCursor(c.block()); sel.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        f = QTextCharFormat(); f.setFontPointSize(size); f.setFontWeight(QFont.Bold if bold else QFont.Normal); f.setFontItalic(italic)
        f.setForeground(QColor(color)); sel.mergeCharFormat(f); c.endEditBlock()
        self.page.mergeCurrentCharFormat(f); self.page.setFocus()

    def sync_format(self, f):
        for b, val in ((self.b_bold, f.fontWeight() >= QFont.Bold), (self.b_ital, f.fontItalic()), (self.b_under, f.fontUnderline()),
                       (self.b_strike, f.fontStrikeOut()), (self.b_sup, f.verticalAlignment() == QTextCharFormat.AlignSuperScript),
                       (self.b_sub, f.verticalAlignment() == QTextCharFormat.AlignSubScript)):
            b.blockSignals(True); b.setChecked(bool(val)); b.blockSignals(False)
        fams = f.fontFamilies()
        fam = fams[0] if fams else KFONT
        self.font_box.blockSignals(True); self.font_box.setCurrentFont(QFont(fam)); self.font_box.blockSignals(False)
        self.size_box.blockSignals(True); self.size_box.setEditText("%g" % (f.fontPointSize() or 12)); self.size_box.blockSignals(False)
        al = self.page.alignment()
        al = int(al.value if hasattr(al, "value") else al) & 0x0f
        for k, b in self.align_btns.items():
            b.blockSignals(True); b.setChecked(k == al or (k == 1 and al == 0)); b.blockSignals(False)

    # ---------- insert
    def page_break(self):
        c = self.page.textCursor(); c.beginEditBlock()
        c.insertBlock(); bf = c.blockFormat(); bf.setPageBreakPolicy(QTextFormat.PageBreak_AlwaysBefore); c.setBlockFormat(bf)
        c.endEditBlock()

    def insert_table(self, r, cols):
        tf = QTextTableFormat(); tf.setBorder(1); tf.setCellPadding(6); tf.setCellSpacing(0); tf.setBorderBrush(QColor("#9aa7b6"))
        tf.setWidth(QTextLength(QTextLength.PercentageLength, 100)); tf.setBorderCollapse(True)
        self.page.textCursor().insertTable(r, cols, tf)

    def insert_picture(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Insert picture", "", "Pictures (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if fn:
            self.insert_image_obj(QImage(fn))

    def insert_image_obj(self, img):
        if img.isNull():
            return
        maxw = self.page.width() - 2 * self.page.document().documentMargin()
        if img.width() > maxw:
            img = img.scaledToWidth(int(maxw), Qt.SmoothTransformation)
        ba = QByteArray(); buf = QBuffer(ba); buf.open(QIODevice.WriteOnly); img.save(buf, "PNG")
        self.page.textCursor().insertHtml('<img src="data:image/png;base64,%s" width="%d" height="%d">' %
                                          (bytes(ba.toBase64()).decode(), img.width(), img.height()))

    def insert_hline(self):
        c = self.page.textCursor(); c.insertHtml("<hr/>"); c.insertBlock()

    def insert_date(self):
        d = date.today()
        self.page.textCursor().insertText("%d\ub144 %d\uc6d4 %d\uc77c" % (d.year, d.month, d.day), self.done_format())

    # ---------- English -> Hangul glue
    def done_format(self, base=None, src=None):
        f = QTextCharFormat(base if base is not None else self.page.currentCharFormat())
        f.setProperty(DONE, True)
        if src: f.setProperty(SRC, src)
        return f

    def clean_typing_format(self):
        """New typing after Hangul must not inherit the 'already converted' tag."""
        if self.page.textCursor().hasSelection():
            return
        f = self.page.currentCharFormat()
        if f.hasProperty(DONE) or f.hasProperty(SRC):
            f.clearProperty(DONE); f.clearProperty(SRC); self.page.setCurrentCharFormat(f)

    def on_cursor(self):
        self.clean_typing_format(); self.update_status()

    def on_change(self, pos, removed, added):
        if self.applying:
            return
        self.hl.start()
        self.idle_long.stop()          # still typing: keep the unfinished sentence whole
        if not self.live or added <= 0:
            return
        last = self.page.document().characterAt(pos + added - 1)
        if added <= 2 and last in ".!?\u2029":
            self.soon.start()          # a sentence just ended
        else:
            self.idle.start()          # convert after a short pause

    def runs_in_block(self, block):
        """English stretches in one paragraph that have not been converted yet: [(start, end, text)]."""
        runs, cur = [], []
        for it in block:
            fr = it.fragment()
            if not fr.isValid():
                continue
            cf = fr.charFormat()
            done = cf.hasProperty(DONE) or cf.isImageFormat()
            for i, ch in enumerate(fr.text()):
                if not done and ord(ch) < 0x2E80 and ch not in "\ufffc\u2028":
                    cur.append((fr.position() + i, ch))
                elif cur:
                    runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        out = []
        for r in runs:
            text = "".join(ch for _, ch in r)
            body = text.strip()
            if not re.search(r"[A-Za-z]", body):
                continue
            start = r[0][0] + (len(text) - len(text.lstrip()))
            out.append((start, start + len(body), body))
        return out

    def queue_run(self, start, end, text):
        for j in self.jobs.values():
            if j["start"] == start and j["src"] == text:
                return
        c = QTextCursor(self.page.document()); c.setPosition(start); c.setPosition(end, QTextCursor.KeepAnchor); c.setKeepPositionOnInsert(True)
        jid = self.next_id; self.next_id += 1
        self.jobs[jid] = {"cur": c, "src": text, "start": start}
        self.worker.submit(jid, text)
        self.update_status()

    def convert_blocks(self, blocks):
        for b in blocks:
            if b.isValid():
                for start, end, text in self.runs_in_block(b):
                    self.queue_run(start, end, text)

    def convert_pending(self, sentences_only):
        """Enter / . ! ? convert what is finished (earlier paragraphs, whole sentences); a pause converts the rest."""
        if not self.live:
            return
        b = self.page.textCursor().block()
        self.convert_blocks([b.previous()])
        for start, end, text in self.runs_in_block(b):
            if sentences_only:
                m = list(re.finditer(r"[.!?](?=[\s\"')\]]|$)", text))
                if not m:
                    continue
                cut = m[-1].end()
                text = text[:cut]; end = start + cut
            self.queue_run(start, end, text)

    def convert_now(self):
        c = self.page.textCursor()
        if c.hasSelection():
            doc = self.page.document(); b = doc.findBlock(c.selectionStart()); last = doc.findBlock(c.selectionEnd())
            blocks = [b]
            while b.isValid() and b.blockNumber() < last.blockNumber():
                b = b.next(); blocks.append(b)
            self.convert_blocks(blocks)
        else:
            self.convert_blocks([c.block()])

    def convert_all(self):
        b = self.page.document().begin(); blocks = []
        while b.isValid():
            blocks.append(b); b = b.next()
        self.convert_blocks(blocks)
        if not self.jobs:
            self.statusBar().showMessage("No English left \u2014 the whole document is in Hangul.", 4000)

    def on_done(self, jid, src, out, eng):
        job = self.jobs.pop(jid, None)
        if not job:
            return
        c = job["cur"]
        if c.selectedText() != src:          # that text changed meanwhile: retry after the next pause
            if self.live: self.idle.start()
            self.update_status(); return
        probe = QTextCursor(self.page.document()); probe.setPosition(c.selectionStart() + 1)
        fmt = self.done_format(probe.charFormat(), src)
        self.applying = True
        c.setKeepPositionOnInsert(False)
        c.beginEditBlock(); c.insertText(out, fmt); c.endEditBlock()
        self.applying = False
        self.clean_typing_format()
        self.engine_note = "Translator: " + eng
        it = QListWidgetItem("%s\n\u2192 %s" % (textwrap.fill(src, 40), textwrap.fill(out, 26))); it.setToolTip(eng); self.log.insertItem(0, it)
        while self.log.count() > 300:
            self.log.takeItem(self.log.count() - 1)
        self.highlight_pending(); self.update_status()

    def on_failed(self, jid, src, err):
        self.jobs.pop(jid, None)
        self.engine_note = "Couldn't translate right now \u2014 your English is kept (%s)" % err[:80]
        self.update_status()

    def on_ready(self, err):
        if err:
            self.engine_note = "Built-in translator unavailable (%s)" % err[:80]
        else:
            self.engine_note = {"auto": "Translator ready: online, built-in backup", "offline": "Translator ready: built-in (offline)",
                                "online": "Translator: online only"}[self.tr.mode]
        self.update_status()

    def highlight_pending(self):
        sels = []
        b = self.page.document().begin()
        while b.isValid():
            for start, end, _ in self.runs_in_block(b):
                s = QTextEdit.ExtraSelection(); c = QTextCursor(self.page.document()); c.setPosition(start); c.setPosition(end, QTextCursor.KeepAnchor)
                f = QTextCharFormat(); f.setBackground(QColor("#eef6e2")); f.setUnderlineStyle(QTextCharFormat.DotLine); f.setUnderlineColor(QColor(GREEN2))
                s.cursor, s.format = c, f; sels.append(s)
            b = b.next()
        self.page.setExtraSelections(sels)

    def set_live(self, on):
        self.live = bool(on); self.settings.setValue("live", "true" if self.live else "false")
        for b in (self.live_pill, self.live_btn, self.live_btn_home):
            b.blockSignals(True); b.setChecked(self.live); b.blockSignals(False)
        self.live_pill.setText("  \u25cf  Live Hangul: ON  " if self.live else "  \u25cb  Live Hangul: OFF  ")
        self.update_status()

    def set_engine(self, mode):
        self.tr.mode = mode; self.tr._online_down_until = 0; self.settings.setValue("engine", mode)
        if mode != "online":
            threading.Thread(target=self.tr.offline.load, daemon=True).start()
        self.on_ready("")

    def set_hangulize(self, on):
        self.tr.hangulize = bool(on); self.settings.setValue("hangulize", "true" if on else "false")

    # ---------- status / title
    def update_status(self):
        if not hasattr(self, "st_live"):
            return
        text = self.page.document().toPlainText()
        words = len(re.findall(r"\S+", text)); hangul = len(hwt.HANGUL_RE.findall(text))
        ph = max(1, self.page.page_h)
        total = max(1, self.page.height() // ph)
        cur = min(total, 1 + max(0, self.page.cursorRect().top()) // ph)
        self.st_page.setText("Page %d of %d" % (cur, total))
        self.st_words.setText("%d words  \u00b7  %d \ud55c\uae00 characters" % (words, hangul))
        pend = len(self.jobs)
        self.st_engine.setText(("Converting %d\u2026   " % pend if pend else "") + self.engine_note + "   ")
        self.st_live.setText("  Live Hangul %s  " % ("ON" if self.live else "OFF"))

    def doc_name(self):
        return os.path.basename(self.path) if self.path else "Document%d" % self.untitled_n

    def update_title(self):
        mod = "*" if self.page.document().isModified() else ""
        self.setWindowTitle("%s%s - %s" % (self.doc_name(), mod, APP_NAME))
        self.title_lbl.setText("%s%s  \u2014  %s" % (self.doc_name(), mod, APP_NAME))

    # ---------- files
    def maybe_save(self):
        if not self.page.document().isModified() or not self.page.document().toPlainText().strip():
            return True
        r = QMessageBox.question(self, APP_NAME, "Save changes to %s?" % self.doc_name(),
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def base_format(self):
        f = QTextCharFormat(); f.setFontFamilies([KFONT]); f.setFontPointSize(12); f.setForeground(QColor("#111111"))
        return f

    def new_doc(self, ask=True):
        if ask:
            if not self.maybe_save():
                return
            self.untitled_n += 1
        self.jobs.clear(); self.path = None
        self.applying = True
        self.page.clear(); self.page.document().setDefaultFont(QFont(KFONT, 12)); self.page.setCurrentCharFormat(self.base_format())
        self.applying = False
        self.page.setPlaceholderText("Start typing in English \u2014 it turns into \ud55c\uae00 when you finish a sentence.")
        self.page.document().setModified(False); self.log.clear(); self.update_title(); self.page.setFocus()

    def open_doc(self):
        if not self.maybe_save():
            return
        fn, _ = QFileDialog.getOpenFileName(self, "Open", self.settings.value("dir", ""),
                                            "HANGUL WOOD documents (*.hwd);;Text (*.txt);;Web page (*.html *.htm);;All files (*.*)")
        if fn:
            self.load(fn)

    def load(self, fn):
        try:
            txt = open(fn, "rb").read().decode("utf-8-sig", "replace")
            ext = os.path.splitext(fn)[1].lower()
            self.applying = True; self.jobs.clear()
            if ext == ".hwd":
                data = json.loads(txt)
                if data.get("page") in PAGES: self.page_name = data["page"]
                if data.get("margin") in MARGINS: self.margin_name = data["margin"]
                self.page.setHtml(data.get("html", ""))
            elif ext in (".html", ".htm"):
                self.page.setHtml(txt)
            else:
                self.page.clear(); self.page.textCursor().insertText(txt, self.base_format())
            self.applying = False
            self.apply_page()
            self.path = fn; self.settings.setValue("dir", os.path.dirname(fn))
            self.page.document().setModified(False); self.update_title(); self.highlight_pending()
        except Exception as e:
            self.applying = False
            QMessageBox.warning(self, APP_NAME, "Couldn't open that file.\n\n%s" % e)

    def save(self):
        if not self.path or os.path.splitext(self.path)[1].lower() not in (".hwd", ".txt"):
            return self.save_as()
        return self.write(self.path)

    def save_as(self):
        start = os.path.join(self.settings.value("dir", "") or os.path.expanduser("~"), os.path.splitext(self.doc_name())[0] + ".hwd")
        fn, flt = QFileDialog.getSaveFileName(self, "Save As", start, "HANGUL WOOD document (*.hwd);;Plain text (*.txt)")
        if not fn:
            return False
        if not os.path.splitext(fn)[1]:
            fn += ".txt" if "txt" in flt else ".hwd"
        if self.write(fn):
            self.path = fn; self.settings.setValue("dir", os.path.dirname(fn)); self.update_title(); return True
        return False

    def write(self, fn):
        try:
            if fn.lower().endswith(".txt"):
                data = self.page.toPlainText().encode("utf-8")
            else:
                data = json.dumps({"app": APP_NAME, "format": 1, "version": APP_VERSION, "page": self.page_name,
                                   "margin": self.margin_name, "html": self.page.toHtml()}, ensure_ascii=False).encode("utf-8")
            tmp = fn + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, fn)
            self.page.document().setModified(False); self.update_title()
            self.statusBar().showMessage("Saved %s" % os.path.basename(fn), 3000)
            return True
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, "Couldn't save.\n\n%s" % e); return False

    def page_size(self):
        return QPageSize(QPageSize.A4 if self.page_name == "A4" else QPageSize.Letter)

    def print_to(self, device):
        doc = self.page.document().clone(); doc.setDocumentMargin(0)
        m = MARGINS.get(self.margin_name, 96) / 96 * 25.4
        device.setPageMargins(QMarginsF(m, m, m, m), QPageLayout.Millimeter)
        doc.print_(device)

    def print_doc(self):
        try:
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        except Exception:
            QMessageBox.information(self, APP_NAME, "Printing isn't available here \u2014 use Export PDF."); return
        pr = QPrinter(QPrinter.HighResolution); pr.setPageSize(self.page_size())
        if QPrintDialog(pr, self).exec() == QDialog.Accepted:
            self.print_to(pr)

    def export_pdf(self):
        start = os.path.join(self.settings.value("dir", "") or os.path.expanduser("~"), os.path.splitext(self.doc_name())[0] + ".pdf")
        fn, _ = QFileDialog.getSaveFileName(self, "Export PDF", start, "PDF (*.pdf)")
        if fn:
            self.write_pdf(fn)
            self.statusBar().showMessage("Exported %s" % os.path.basename(fn), 4000)

    def write_pdf(self, fn):
        w = QPdfWriter(fn); w.setPageSize(self.page_size()); w.setResolution(300)
        w.setCreator(APP_NAME); w.setTitle(os.path.splitext(self.doc_name())[0])
        self.print_to(w)

    def export_html(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Export web page", os.path.splitext(self.doc_name())[0] + ".html", "Web page (*.html)")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.page.toHtml())

    def about(self):
        d = QDialog(self); d.setWindowTitle("About " + APP_NAME); d.setFixedWidth(460)
        v = QVBoxLayout(d)
        art = QLabel(); art.setAlignment(Qt.AlignCenter)
        art.setPixmap(QPixmap(res("assets", "wordmark512.jpg")).scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v.addWidget(art)
        t = QLabel("<b>HANGUL WOOD</b> %s<br>Type English \u2014 your document fills with \ud55c\uae00.<br><br>%s<br><br>"
                   "<span style='color:#5e6b7a'>Built-in English\u2192Korean model: Argos Translate (OPUS data) running on CTranslate2 + SentencePiece, "
                   "fully offline. Auto / Online mode sends each finished sentence over HTTPS to a public translation service for "
                   "higher quality and falls back to the built-in model when the network is down.<br>"
                   "Font: Noto Sans KR (SIL Open Font License).</span>" % (APP_VERSION, COPYRIGHT))
        t.setWordWrap(True); t.setAlignment(Qt.AlignCenter); v.addWidget(t)
        ok = QPushButton("OK"); ok.clicked.connect(d.accept); v.addWidget(ok, 0, Qt.AlignCenter)
        d.exec()

    def closeEvent(self, e):
        if self.maybe_save():
            self.settings.setValue("ruler", "true" if self.ruler.isVisible() else "false")
            self.settings.setValue("log", "true" if self.dock.isVisible() else "false")
            e.accept()
        else:
            e.ignore()


SIZES = [8, 9, 10, 10.5, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72]

STYLE = """
QMainWindow { background: %(CANVAS)s; }
QFrame#band { background: %(NAVY)s; }
QLabel#title { color: white; font-size: 13px; font-weight: 600; }
QToolButton#qa { border-radius: 4px; padding: 3px; }
QToolButton#qa:hover { background: %(NAVY2)s; border-color: %(NAVY2)s; }
QPushButton#pill { color: %(NAVY)s; background: %(GREEN)s; border: none; border-radius: 12px; padding: 4px 6px; font-weight: 700; font-size: 12px; }
QPushButton#pill:!checked { background: #50627c; color: #dfe6ef; }
QFrame#strip { background: white; border-bottom: 1px solid %(LINE)s; }
QToolButton#filebtn { background: %(GREEN)s; color: %(NAVY)s; font-weight: 700; padding: 5px 16px; border: none; border-radius: 3px; font-size: 13px; }
QToolButton#filebtn::menu-indicator { image: none; width: 0px; }
QPushButton#tab { background: transparent; border: none; border-radius: 0; padding: 6px 14px; color: %(INK)s; font-size: 13px; border-bottom: 3px solid transparent; }
QPushButton#tab:hover { color: %(NAVY)s; background: #f0f4f8; }
QPushButton#tab:checked { color: %(NAVY)s; font-weight: 700; border-bottom: 3px solid %(GREEN)s; }
QLabel#hint { color: %(MUTED)s; font-size: 12px; padding-right: 6px; }
QStackedWidget#ribbon, QStackedWidget#ribbon > QWidget { background: %(RIBBON)s; }
QLabel#cap { color: %(MUTED)s; font-size: 11px; }
QFrame#gsep { color: %(LINE)s; margin: 6px 2px 8px 2px; }
QToolButton { color: %(INK)s; border: 1px solid transparent; border-radius: 4px; padding: 2px; font-size: 12px; }
QToolButton:hover { background: #e4ebf2; border-color: #cfd8e2; }
QToolButton:checked { background: #dcebc6; border-color: #a9cc78; }
QToolButton::menu-indicator { width: 0px; image: none; }
QToolButton#style { background: white; border: 1px solid %(LINE)s; font-size: 11px; color: %(NAVY)s; }
QToolButton#style:hover { border-color: %(GREEN)s; }
QPushButton { background: white; border: 1px solid %(LINE)s; border-radius: 4px; padding: 3px 10px; color: %(INK)s; }
QPushButton:hover { border-color: %(GREEN)s; }
QPushButton#radio { text-align: left; padding: 3px 10px; }
QPushButton#radio:checked { background: #dcebc6; border-color: %(GREEN2)s; color: %(NAVY)s; font-weight: 600; }
QComboBox, QFontComboBox { background: white; border: 1px solid %(LINE)s; border-radius: 3px; padding: 2px 6px; min-height: 22px; color: %(INK)s; }
QScrollArea#canvas, QWidget#canvasw { background: %(CANVAS)s; }
QFrame#sheet { background: white; border: 1px solid #c7d0db; }
QStatusBar { background: %(NAVY)s; color: #e6edf5; }
QStatusBar QLabel { color: #e6edf5; font-size: 12px; }
QStatusBar::item { border: none; }
QDockWidget { color: %(NAVY)s; font-weight: 700; }
QDockWidget::title { background: white; padding: 8px; border-bottom: 2px solid %(GREEN)s; }
QListWidget#log { background: white; border: none; font-size: 13px; }
QListWidget#log::item { padding: 8px; border-bottom: 1px solid #edf1f5; color: %(INK)s; }
QListWidget#log::item:selected { background: #e4efd6; }
QMenu { background: white; border: 1px solid %(LINE)s; padding: 4px; color: %(INK)s; }
QMenu::item { padding: 6px 26px 6px 10px; }
QMenu::item:selected { background: #e4efd6; color: %(NAVY)s; }
QDialog { background: white; }
QScrollBar:vertical { background: %(CANVAS)s; width: 12px; margin: 0; }
QScrollBar:horizontal { background: %(CANVAS)s; height: 12px; margin: 0; }
QScrollBar::handle { background: #b6c1cd; border-radius: 5px; min-height: 30px; min-width: 30px; margin: 2px; }
QScrollBar::handle:hover { background: #8e9cac; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
""" % dict(NAVY=NAVY, NAVY2=NAVY2, GREEN=GREEN, GREEN2=GREEN2, INK=INK, MUTED=MUTED, LINE=LINE, RIBBON=RIBBON, CANVAS=CANVAS)


def main():
    global KFONT
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setOrganizationName("EX Inc"); app.setWindowIcon(QIcon(res("assets", "logo.ico")))
    fams = []
    for fn in ("NotoSansKR-Regular.otf", "NotoSansKR-Bold.otf"):
        fid = QFontDatabase.addApplicationFont(res("fonts", fn))
        if fid >= 0 and not fams:
            fams = QFontDatabase.applicationFontFamilies(fid)
    KFONT = fams[0] if fams else ("Malgun Gothic" if os.name == "nt" else "Sans Serif")
    hw_icons.KFONT = KFONT
    f = QFont(KFONT); f.setPixelSize(12); app.setFont(f)
    path = next((a for a in sys.argv[1:] if not a.startswith("--") and os.path.isfile(a)), None)
    w = Main(path); w.show()
    if "--demo-shot" in sys.argv:
        import hw_demo
        hw_demo.run(w, sys.argv[sys.argv.index("--demo-shot") + 1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
