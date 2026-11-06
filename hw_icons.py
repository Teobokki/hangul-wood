"""HANGUL WOOD ribbon icons, drawn in code (original artwork). ©2026 EX Inc./HYPERION DIGITAL ©2026"""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QIcon, QPixmap, QFont, QColor, QPainter, QPen, QPainterPath

NAVY, GREEN, GREEN2, INK, MUTED = "#0f2e57", "#8cbf3f", "#6fa22a", "#1d2733", "#5e6b7a"
KFONT = "Noto Sans KR"


def make_icon(kind, color=INK, size=32):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 32.0, size / 32.0)
    p.setPen(QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    g = QColor(GREEN)
    P = QPointF

    def lines(xs, ys=(8, 13, 18, 23)):
        for (x0, x1), y in zip(xs, ys):
            p.drawLine(P(x0, y), P(x1, y))

    def poly(pts, close=True):
        path = QPainterPath(); path.moveTo(*pts[0])
        for pt in pts[1:]:
            path.lineTo(*pt)
        if close:
            path.closeSubpath()
        p.drawPath(path)

    def txt(rect, s, px, bold=True, fam="Arial", col=None):
        f = QFont(fam); f.setPixelSize(px); f.setBold(bold); p.setFont(f)
        if col: p.setPen(QColor(col))
        p.drawText(QRectF(*rect), Qt.AlignCenter, s)

    if kind == "left": lines([(5, 27), (5, 19), (5, 27), (5, 19)])
    elif kind == "center": lines([(5, 27), (9, 23), (5, 27), (9, 23)])
    elif kind == "right": lines([(5, 27), (13, 27), (5, 27), (13, 27)])
    elif kind == "justify": lines([(5, 27)] * 4)
    elif kind in ("bullets", "numbers"):
        for i, y in enumerate((9, 16, 23)):
            if kind == "bullets":
                p.setBrush(QColor(color)); p.drawEllipse(P(7, y), 1.6, 1.6); p.setBrush(Qt.NoBrush)
            p.drawLine(P(12, y), P(27, y))
        if kind == "numbers":
            for i, y in enumerate((9, 16, 23)):
                txt((1, y - 5, 9, 10), str(i + 1), 7)
    elif kind in ("indent", "outdent"):
        lines([(5, 27), (14, 27), (14, 27), (5, 27)])
        p.setPen(QPen(g, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        poly([(5, 11), (10, 15.5), (5, 20)] if kind == "indent" else [(10, 11), (5, 15.5), (10, 20)], close=False)
    elif kind in ("undo", "redo"):
        path = QPainterPath()
        if kind == "undo":
            path.moveTo(9, 13); path.cubicTo(14, 7, 27, 8, 26, 19); path.lineTo(25, 24)
            p.drawPath(path); p.drawPolyline([P(8, 6.5), P(8, 13.5), P(15, 13.5)])
        else:
            path.moveTo(23, 13); path.cubicTo(18, 7, 5, 8, 6, 19); path.lineTo(7, 24)
            p.drawPath(path); p.drawPolyline([P(24, 6.5), P(24, 13.5), P(17, 13.5)])
    elif kind == "save":
        p.drawRoundedRect(QRectF(5, 5, 22, 22), 2.5, 2.5); p.drawRect(QRectF(10, 5, 11, 7)); p.drawRect(QRectF(9, 17, 14, 10))
    elif kind in ("new", "pdf"):
        poly([(7, 4), (19, 4), (25, 10), (25, 28), (7, 28)]); p.drawPolyline([P(19, 4), P(19, 10), P(25, 10)])
        if kind == "pdf": txt((7, 14, 18, 10), "PDF", 7, col="#c0392b")
    elif kind == "open":
        p.drawPolyline([P(4, 25), P(4, 8), P(12, 8), P(14, 11), P(24, 11), P(24, 15)])
        poly([(4, 25), (9, 15), (29, 15), (24, 25)])
    elif kind == "paste":
        p.drawRoundedRect(QRectF(5, 7, 18, 21), 2, 2); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(10, 4, 8, 5), 1.5, 1.5)
        p.setBrush(QColor("white")); p.drawRect(QRectF(14, 13, 13, 16)); p.setBrush(Qt.NoBrush)
    elif kind == "cut":
        p.drawEllipse(P(10, 23), 3.5, 3.5); p.drawEllipse(P(22, 23), 3.5, 3.5)
        p.drawLine(P(12, 20), P(22, 5)); p.drawLine(P(20, 20), P(10, 5))
    elif kind == "copy":
        p.drawRoundedRect(QRectF(5, 5, 14, 17), 2, 2); p.setBrush(QColor("white")); p.drawRoundedRect(QRectF(12, 11, 14, 17), 2, 2)
    elif kind == "color":
        txt((0, 0, 32, 24), "A", 18); p.fillRect(QRectF(5, 24, 22, 5), QColor("#d0312d"))
    elif kind == "highlight":
        poly([(9, 20), (20, 5), (25, 9), (14, 23)]); p.fillRect(QRectF(5, 25, 22, 5), QColor("#ffe25a"))
    elif kind == "clear":
        txt((0, 0, 26, 28), "A", 17)
        p.setPen(QPen(QColor("#d0312d"), 2.4)); p.drawLine(P(19, 19), P(28, 28)); p.drawLine(P(28, 19), P(19, 28))
    elif kind == "table":
        p.drawRect(QRectF(5, 6, 22, 20)); p.drawLine(P(5, 12.5), P(27, 12.5)); p.drawLine(P(5, 19), P(27, 19))
        p.drawLine(P(12, 6), P(12, 26)); p.drawLine(P(19.5, 6), P(19.5, 26))
    elif kind == "picture":
        p.drawRoundedRect(QRectF(4, 6, 24, 20), 2, 2); p.setBrush(g); p.setPen(Qt.NoPen)
        poly([(6, 24), (13, 14), (18, 20), (21, 17), (26, 24)]); p.setBrush(QColor(NAVY)); p.drawEllipse(P(22, 11), 2.4, 2.4)
    elif kind == "pagebreak":
        p.drawRect(QRectF(8, 3, 16, 9)); p.drawRect(QRectF(8, 20, 16, 9))
        p.setPen(QPen(g, 2.2, Qt.DashLine)); p.drawLine(P(3, 16), P(29, 16))
    elif kind == "hline":
        p.setPen(QPen(QColor(color), 2.6)); p.drawLine(P(4, 16), P(28, 16))
        p.setPen(QPen(QColor(MUTED), 1.6)); p.drawLine(P(8, 9), P(24, 9)); p.drawLine(P(8, 23), P(24, 23))
    elif kind == "date":
        p.drawRoundedRect(QRectF(5, 7, 22, 20), 2, 2); p.fillRect(QRectF(5, 7, 22, 6), QColor(NAVY))
        p.drawLine(P(11, 4), P(11, 9)); p.drawLine(P(21, 4), P(21, 9)); p.fillRect(QRectF(16, 18, 6, 5), g)
    elif kind == "print":
        p.drawRect(QRectF(9, 4, 14, 8)); p.drawRoundedRect(QRectF(4, 12, 24, 11), 2, 2); p.setBrush(QColor("white")); p.drawRect(QRectF(9, 19, 14, 9))
    elif kind == "convert":
        txt((1, 1, 15, 15), "A", 12)
        txt((14, 13, 18, 18), "\ud55c", 14, fam=KFONT, col=GREEN2)
        p.setPen(QPen(QColor(NAVY), 2)); p.drawLine(P(6, 19), P(11, 25)); p.drawPolyline([P(7, 25), P(11, 25), P(11, 21)])
    elif kind == "convertall":
        p.drawRoundedRect(QRectF(4, 4, 24, 24), 3, 3); txt((4, 3, 24, 24), "\ud55c", 15, fam=KFONT, col=GREEN2)
    elif kind == "live":
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawEllipse(P(16, 16), 12, 12)
        p.setBrush(QColor("white")); poly([(17, 7), (11, 17), (16, 17), (14, 25), (21, 14), (16, 14)])
    elif kind == "log":
        p.drawRoundedRect(QRectF(5, 4, 22, 24), 2, 2); lines([(9, 23), (9, 20), (9, 23), (9, 17)], (10, 15, 20, 25))
    elif kind == "ruler":
        p.drawRect(QRectF(3, 11, 26, 10))
        for x in range(6, 28, 4):
            p.drawLine(P(x, 11), P(x, 15 if x % 8 else 17))
    elif kind in ("zoomin", "zoomout"):
        p.drawEllipse(P(13, 13), 8, 8); p.drawLine(P(19, 19), P(27, 27)); p.drawLine(P(9, 13), P(17, 13))
        if kind == "zoomin": p.drawLine(P(13, 9), P(13, 17))
    elif kind == "margins":
        p.drawRect(QRectF(6, 3, 20, 26)); p.setPen(QPen(g, 1.6, Qt.DashLine)); p.drawRect(QRectF(10, 7, 12, 18))
    elif kind == "pagesize":
        p.drawRect(QRectF(8, 2, 18, 25)); p.setPen(QPen(g, 2)); p.drawLine(P(4, 4), P(4, 27)); p.drawLine(P(8, 30), P(26, 30))
    elif kind == "spacing":
        lines([(13, 28)] * 4); p.setPen(QPen(g, 2))
        p.drawLine(P(6, 6), P(6, 26)); p.drawPolyline([P(3, 9), P(6, 5), P(9, 9)]); p.drawPolyline([P(3, 23), P(6, 27), P(9, 23)])
    p.end()
    return QIcon(pm)
