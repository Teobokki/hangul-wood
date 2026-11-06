"""Screenshot helper: types a short English letter into HANGUL WOOD, lets it turn into Hangul, saves real screenshots."""
import os
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextListFormat
from PySide6.QtWidgets import QApplication

SCRIPT = [("style", "Title"), ("type", "My trip to Seoul\n"), ("style", "Normal"),
          ("type", "Today I visited a beautiful palace with my friends. The weather was warm and sunny. "
                   "We ate spicy noodles for lunch and laughed a lot.\n"),
          ("style", "Heading 2"), ("type", "Plans for tomorrow\n"), ("style", "Normal"), ("list", None),
          ("type", "Visit the national museum.\n"), ("type", "Buy a small gift for my mother.\n"),
          ("type", "Write a letter to Teo.\n"), ("list", None), ("wait", 4000),
          ("type", "I can't wait to write more")]


def run(w, outdir):
    os.makedirs(outdir, exist_ok=True)
    w.resize(1500, 940); w.set_engine(os.environ.get("HW_DEMO_ENGINE", "offline")); w.set_live(True)
    steps = list(SCRIPT)
    page = w.page

    def shot(name):
        QApplication.processEvents()
        w.grab().save(os.path.join(outdir, name))

    def finish():
        shot("shot0.png")
        w.tabs.button(3).click(); QApplication.processEvents(); shot("shot1.png")
        w.tabs.button(1).click(); QApplication.processEvents(); shot("shot2.png")
        w.tabs.button(0).click()
        w.write_pdf(os.path.join(outdir, "demo.pdf"))
        w.page.document().setModified(False)
        QTimer.singleShot(300, QApplication.quit)

    def step():
        if not steps:
            QTimer.singleShot(2500, finish); return
        kind, arg = steps.pop(0)
        if kind == "style":
            w.apply_style(arg); QTimer.singleShot(50, step)
        elif kind == "list":
            w.toggle_list(QTextListFormat.ListDisc); QTimer.singleShot(50, step)
        elif kind == "wait":
            QTimer.singleShot(arg, step)
        else:
            chars = list(arg)

            def key():
                if not chars:
                    QTimer.singleShot(400, step); return
                ch = chars.pop(0)
                c = page.textCursor()
                if ch == "\n":
                    c.insertBlock()
                else:
                    c.insertText(ch)
                page.setTextCursor(c)
                QTimer.singleShot(12, key)
            key()
    QTimer.singleShot(2500, step)
