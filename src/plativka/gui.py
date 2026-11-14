"""
Платівка / Plativka — віконна версія (Qt) для macOS, Windows і Linux.

Той самий плеєр, що й у терміналі (ядро — core.py: медіатека, теги, обкладинки, mpv),
але у звичайному вікні: справжні обкладинки, табло з годинником, компактний вигляд
і міні-плеєр. На Windows 11 фон вікна — напівпрозорий Mica.

Запуск:  plativka-desktop            звичайний режим
         plativka-desktop --demo     без mpv і без звуку
         plativka-desktop --lang=en  мова інтерфейсу (uk / en)
"""
from __future__ import annotations

import asyncio
import io
import json
import html
import os
import random
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer, Signal, QObject
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QFontMetrics, QIcon,
                           QImage, QKeySequence, QPainter, QPainterPath, QPalette, QPixmap, QShortcut)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QRadioButton, QSizePolicy, QSlider, QStackedWidget, QSystemTrayIcon,
                               QSpacerItem, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QTableWidgetItem, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import skins, sysdeps, sysvol
from .remote import RemoteHost
from .core import (APP_NAME, AUDIO_EXT, AUTHOR, CACHE_DIR, CONF_DIR, GITHUB_URL, ISSUES_URL, VERSION,
                   SLEEP_CHOICES, DemoPlayer, Library, MpvPlayer, PlayerExtras, Track, accent_from,
                   UPDATE_EVERY, check_update, clamp, fmt_time, load_cover, log, read_track, real_path, rgb_hex, rotate_log,
                   scan_dir, tune)
from .i18n import LANG, _, n_tracks

DEFAULT_ACCENT = (14, 124, 132)
CFG_FILE = CONF_DIR / "desktop.json"


# ═══════════════════════════════ дрібниці ═══════════════════════════════
def pil_to_pixmap(im) -> QPixmap:
    im = im.convert("RGBA")
    qi = QImage(im.tobytes(), im.width, im.height, im.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qi.copy())


def rounded(pix: QPixmap, size: int, radius: float) -> QPixmap:
    dpr = 2.0
    out = QPixmap(int(size * dpr), int(size * dpr))
    out.setDevicePixelRatio(dpr)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(path)
    if pix is not None and not pix.isNull():
        src = pix.scaled(int(size * dpr), int(size * dpr), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap(QRectF(0, 0, size, size), src, QRectF(0, 0, src.width(), src.height()))
    p.end()
    return out


def placeholder_cover(accent: str, dark: bool) -> QPixmap:
    """Платівка замість обкладинки."""
    s = 400
    pix = QPixmap(s, s)
    pix.fill(QColor("#2A2E37" if dark else "#DCE1EA"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#15171C"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(s / 2, s / 2), s * .42, s * .42)
    p.setPen(QColor(255, 255, 255, 22))
    p.setBrush(Qt.NoBrush)
    for r in range(60, 168, 9):
        p.drawEllipse(QPointF(s / 2, s / 2), r, r)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(accent))
    p.drawEllipse(QPointF(s / 2, s / 2), s * .14, s * .14)
    p.setBrush(QColor("#15171C"))
    p.drawEllipse(QPointF(s / 2, s / 2), 6, 6)
    p.end()
    return pix


def glyph_icon(kind: str, color: str, size: int = 16) -> QIcon:
    """Прості векторні значки кнопок — однакові на всіх системах (без кольорових емодзі Windows)."""
    dpr = 3
    pix = QPixmap(size * dpr, size * dpr)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    s = float(size)

    def tri(x0, x1, y0=s * .2, y1=s * .8):
        path = QPainterPath()
        path.moveTo(x0, y0)
        path.lineTo(x1, (y0 + y1) / 2)
        path.lineTo(x0, y1)
        path.closeSubpath()
        p.drawPath(path)

    def tri_l(x0, x1, y0=s * .2, y1=s * .8):
        path = QPainterPath()
        path.moveTo(x1, y0)
        path.lineTo(x0, (y0 + y1) / 2)
        path.lineTo(x1, y1)
        path.closeSubpath()
        p.drawPath(path)

    if kind == "play":
        tri(s * .3, s * .8)
    elif kind == "pause":
        p.drawRoundedRect(QRectF(s * .26, s * .22, s * .16, s * .56), 1, 1)
        p.drawRoundedRect(QRectF(s * .58, s * .22, s * .16, s * .56), 1, 1)
    elif kind == "stop":
        p.drawRoundedRect(QRectF(s * .27, s * .27, s * .46, s * .46), 1.5, 1.5)
    elif kind == "next":
        tri(s * .2, s * .52)
        tri(s * .48, s * .8)
        p.drawRect(QRectF(s * .8, s * .2, s * .08, s * .6))
    elif kind == "prev":
        tri_l(s * .48, s * .8)
        tri_l(s * .2, s * .52)
        p.drawRect(QRectF(s * .12, s * .2, s * .08, s * .6))
    elif kind == "eject":
        path = QPainterPath()
        path.moveTo(s * .2, s * .58)
        path.lineTo(s * .5, s * .22)
        path.lineTo(s * .8, s * .58)
        path.closeSubpath()
        p.drawPath(path)
        p.drawRect(QRectF(s * .2, s * .68, s * .6, s * .1))
    elif kind in ("up", "down"):
        path = QPainterPath()
        if kind == "up":
            path.moveTo(s * .25, s * .64); path.lineTo(s * .5, s * .34); path.lineTo(s * .75, s * .64)
        else:
            path.moveTo(s * .25, s * .36); path.lineTo(s * .5, s * .66); path.lineTo(s * .75, s * .36)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "pin":
        p.drawEllipse(QPointF(s * .5, s * .32), s * .2, s * .2)
        p.drawRect(QRectF(s * .46, s * .45, s * .08, s * .4))
    elif kind == "menu":
        for y in (.28, .48, .68):
            p.drawRoundedRect(QRectF(s * .2, s * y, s * .6, s * .08), 1, 1)
    p.end()
    return QIcon(pix)


def app_icon() -> QIcon:
    ic = sysdeps.icon_path()
    if ic and sys.platform == "darwin":
        # у доці macOS іконка має поля й тінь, як системні, інакше вона здається більшою
        mac = Path(ic).with_name("icon-mac.png")
        if mac.exists():
            ic = str(mac)
    return QIcon(ic) if ic else QIcon()


# ═══════════════════════════════ віджети ═══════════════════════════════
class Clickable(QLabel):
    clicked = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


class ElidedLabel(QLabel):
    """Рядок, що не влазить, закінчується «…», а не обривається на півслові."""

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(self.palette().windowText().color())
        p.setFont(self.font())
        fm = QFontMetrics(self.font())
        r = self.contentsRect()
        p.drawText(r, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(self.text(), Qt.ElideRight, r.width()))
        p.end()


class CoverLabel(QLabel):
    clicked = Signal()

    def __init__(self, size: int):
        super().__init__()
        self._pix = None
        self.set_size(size)
        self.setCursor(Qt.PointingHandCursor)

    def set_size(self, size: int):
        self._size = size
        self.setFixedSize(size, size)
        self._redraw()

    def set_cover(self, pix: QPixmap):
        self._pix = pix
        self._redraw()

    def _redraw(self):
        if self._pix is not None:
            self.setPixmap(rounded(self._pix, self._size, 7 if self._size > 80 else 5))

    def mousePressEvent(self, e):
        self.clicked.emit()


SEGMENTS = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd',
            '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg', '-': 'g', ' ': ''}


class LcdClock(QWidget):
    """Великий годинник із семисегментних цифр, як на табло Winamp."""
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.text = "-:--"
        self.color = QColor("#0E7C84")
        self.setMinimumSize(110, 44)
        self.setMaximumHeight(48)
        self.setCursor(Qt.PointingHandCursor)

    def set_text(self, t: str):
        if t != self.text:
            self.text = t
            self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h = self.height()
        w = h * .5
        th = max(3.0, h * .11)
        on = QColor(self.color)
        off = QColor(self.color)
        off.setAlpha(26)
        total = sum(th * 2.2 if c == ':' else w + th * 1.1 for c in self.text)
        x = max(0.0, (self.width() - total) / 2)
        p.setPen(Qt.NoPen)
        for ch in self.text:
            if ch == ':':
                p.setBrush(on)
                p.drawRoundedRect(QRectF(x + th * .4, h * .27, th, th), 2, 2)
                p.drawRoundedRect(QRectF(x + th * .4, h * .63, th, th), 2, 2)
                x += th * 2.2
                continue
            segs = {'a': (0, 0, w, th), 'd': (0, h - th, w, th), 'g': (0, h / 2 - th / 2, w, th),
                    'f': (0, 0, th, h / 2), 'b': (w - th, 0, th, h / 2),
                    'e': (0, h / 2, th, h / 2), 'c': (w - th, h / 2, th, h / 2)}
            lit = SEGMENTS.get(ch, '')
            for k, (sx, sy, sw, sh) in segs.items():
                p.setBrush(on if k in lit else off)
                p.drawRoundedRect(QRectF(x + sx + 1, sy + 1, sw - 2, sh - 2), 2, 2)
            x += w + th * 1.1
        p.end()


class LevelBars(QWidget):
    """Візуалізація звуку вертикальними «світлодіодними» стовпчиками.

    Посередині — щойно зігране, до країв — кілька секунд тому: ліворуч лівий канал,
    праворуч правий. Тож видно і гучність, і стерео, і як вона змінювалась.
    """

    def __init__(self, cols: int = 16, rows: int = 7):
        super().__init__()
        from collections import deque
        self.cols, self.rows = cols, rows
        half = cols // 2
        self.hist = [deque([0.0] * half, maxlen=half), deque([0.0] * half, maxlen=half)]
        self.color = QColor("#0E7C84")
        self.dark = False
        self.enabled_ = True

    def show_levels(self, levels, peaks, ok):
        self.enabled_ = ok
        for ch in (0, 1):
            self.hist[ch].append(levels[ch] if ok else 0.0)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        half = self.cols // 2
        gap_mid = 4.0
        cw = (self.width() - gap_mid) / self.cols
        rh = self.height() / self.rows
        off = QColor(255, 255, 255, 26) if self.dark else QColor(0, 0, 0, 22)
        warm, hot = QColor(226, 168, 34), QColor(222, 80, 58)
        for c in range(self.cols):
            if c < half:
                v = self.hist[0][c]                    # ліворуч: старіше → новіше до центру
                x = c * cw
            else:
                v = self.hist[1][self.cols - 1 - c]    # праворуч: новіше біля центру
                x = c * cw + gap_mid
            lit = round(v * self.rows)
            age = (c if c < half else self.cols - 1 - c) / max(1, half - 1)   # 0 — найстаріше
            for r in range(self.rows):
                f = r / max(1, self.rows - 1)
                if r < lit:
                    col = QColor(self.color) if f < .6 else (warm if f < .85 else hot)
                    col.setAlphaF(0.6 + 0.4 * age)
                else:
                    col = off
                p.setBrush(col)
                y = self.height() - (r + 1) * rh
                p.drawRoundedRect(QRectF(x + 1, y + 1, cw - 2.5, rh - 2), 1.2, 1.2)
        p.end()


class SeekSlider(QSlider):
    """Смуга перемотування: клік — одразу в це місце (а не «крок» як у звичайного повзунка)."""
    seek = Signal(float)

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.setRange(0, 1000)
        self.setCursor(Qt.PointingHandCursor)
        self.dragging = False
        self.sliderPressed.connect(lambda: setattr(self, "dragging", True))
        self.sliderReleased.connect(self._released)

    def _released(self):
        self.dragging = False
        self.seek.emit(self.value() / 1000)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            v = round(e.position().x() / max(1, self.width()) * 1000)
            self.setValue(int(clamp(v, 0, 1000)))
            self.dragging = True
        super().mousePressEvent(e)


class TrackTable(QTableWidget):
    activated_row = Signal(int)
    delete_pressed = Signal()

    def __init__(self):
        super().__init__(0, 4)
        self.setHorizontalHeaderLabels(["#", _("Трек"), _("Час"), ""])
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.ElideRight)
        h = self.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Fixed)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        self.setColumnWidth(0, 56)
        self.setColumnWidth(2, 50)
        self.setColumnWidth(3, 24)             # сердечко: ♥ — улюблений, ♡ — лише під курсором чи на виділеному
        self.setMouseTracking(True)
        self.hover_row = -1
        self.verticalHeader().setDefaultSectionSize(22)
        self.setAlternatingRowColors(False)
        self.cellDoubleClicked.connect(lambda r, c: self.activated_row.emit(r))
        self.setFocusPolicy(Qt.StrongFocus)

    hover_changed = Signal(int, int)

    def mouseMoveEvent(self, e):
        r = self.rowAt(int(e.position().y()))
        if r != self.hover_row:
            old, self.hover_row = self.hover_row, r
            self.hover_changed.emit(old, r)
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        if self.hover_row != -1:
            old, self.hover_row = self.hover_row, -1
            self.hover_changed.emit(old, -1)
        super().leaveEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.currentRow() >= 0:
            self.activated_row.emit(self.currentRow())
            return
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_pressed.emit()
            return
        super().keyPressEvent(e)


class CurrentMark(QStyledItemDelegate):
    """Рядок, що грає: у скіні «macOS» — заокруглена плашка кольору обкладинки на весь рядок,
    у «Windows 11» — легка плашка й коротка вертикальна риска зліва."""

    def __init__(self, win):
        super().__init__(win.table)
        self.win = win

    def paint(self, p, opt, idx):
        w = self.win
        cur = idx.row() == w.current and w.skin in ("mac", "fluent") and hasattr(w, "_acc")
        if cur:
            vp = w.table.viewport().width()
            r = opt.rect
            a = QColor(w._acc)
            if w.skin == "fluent":
                a.setAlpha(46)
            p.save()
            p.setRenderHint(QPainter.Antialiasing)
            p.setClipRect(r)
            p.setPen(Qt.NoPen)
            p.setBrush(a)
            rad = 6 if w.skin == "mac" else 4
            p.drawRoundedRect(QRectF(2, r.top() + 1, vp - 4, r.height() - 2), rad, rad)
            p.restore()
            # виділення поверх цієї плашки робило текст нечитабельним (темне на темному)
            opt = QStyleOptionViewItem(opt)
            opt.state &= ~(QStyle.State_Selected | QStyle.State_MouseOver | QStyle.State_HasFocus)
        super().paint(p, opt, idx)
        if w.skin == "fluent" and idx.row() == w.current and idx.column() == 0:
            r = opt.rect
            p.save()
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(w._acc))
            h = min(16, r.height() - 8)
            p.drawRoundedRect(QRectF(r.left() + 3, r.center().y() - h / 2 + 1, 3, h), 1.5, 1.5)
            p.restore()


class LibraryTree(QTreeWidget):
    activated_item = Signal(object)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setColumnCount(2)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.setIndentation(16)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.itemActivated.connect(lambda it, c: self.activated_item.emit(it))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and self.currentItem() is not None:
            self.activated_item.emit(self.currentItem())
            return
        super().keyPressEvent(e)


class RemoteDialog(QDialog):
    """Пульт з телефона: увімкнути, QR-код, ручний код, підключені телефони."""

    def __init__(self, win: "MainWindow"):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(_("Пульт з телефона"))
        self.resize(440, 470)
        lay = QVBoxLayout(self)
        self.on = QCheckBox(_("Дозволити керування з телефона"))
        self.on.setChecked(win.remote is not None and win.remote.running)
        self.on.toggled.connect(lambda v: win.spawn(self._toggle(v)))
        lay.addWidget(self.on)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setObjectName("dim")
        lay.addWidget(self.hint)
        row = QHBoxLayout()
        self.qr = QLabel()
        self.qr.setFixedSize(176, 176)
        self.qr.setAlignment(Qt.AlignCenter)
        row.addWidget(self.qr)
        side = QVBoxLayout()
        self.how = QLabel()
        self.how.setWordWrap(True)
        self.how.setTextInteractionFlags(Qt.TextSelectableByMouse)
        side.addWidget(self.how)
        self.code_btn = QPushButton(_("Показати код"))
        self.code_btn.clicked.connect(self._code)
        side.addWidget(self.code_btn)
        self.code = QLabel()
        self.code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f = self.code.font()
        f.setPointSizeF(f.pointSizeF() * 2.2)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        self.code.setFont(f)
        side.addWidget(self.code)
        self.code_left = QLabel()
        self.code_left.setObjectName("dim")
        side.addWidget(self.code_left)
        side.addStretch()
        row.addLayout(side, 1)
        lay.addLayout(row)
        lay.addSpacing(10)                      # біле поле QR-коду не злипається з підписом
        lay.addWidget(QLabel(_("Підключені телефони")))
        self.list = QListWidget()
        self.list.setMaximumHeight(self.list.fontMetrics().height() * 4 + 16)
        lay.addWidget(self.list)
        brow = QHBoxLayout()
        self.forget_btn = QPushButton(_("Відключити вибраний"))
        self.forget_btn.clicked.connect(self._forget)
        self.reset_btn = QPushButton(_("Відключити всіх і змінити QR-код"))
        self.reset_btn.clicked.connect(self._reset)
        brow.addWidget(self.forget_btn)
        brow.addStretch()
        brow.addWidget(self.reset_btn)
        lay.addLayout(brow)
        note = QLabel(_("Працює лише у вашій домашній мережі і лише поки відкрита Платівка. "
                        "Не вмикайте в публічних Wi-Fi (кафе, готель)."))
        note.setWordWrap(True)
        note.setObjectName("dim")
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Close).setText(_("Закрити"))
        lay.addWidget(bb)
        self._qr_for = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.finished.connect(self._closed)
        self.refresh()

    def _closed(self, *_):
        if self.win.remote:
            self.win.remote.rotate_secret()     # показаний QR-код після закриття вікна не діє

    async def _toggle(self, on: bool):
        await self.win.set_remote(on)
        self.refresh()

    def _code(self):
        if self.win.remote and self.win.remote.running:
            self.win.remote.new_code()
            self.refresh()

    def _forget(self):
        it = self.list.currentItem()
        if it is not None and self.win.remote:
            self.win.remote.forget(it.data(Qt.UserRole))
            self.refresh()

    def _reset(self):
        if self.win.remote:
            self.win.remote.reset_pairing()
            self.refresh()

    def refresh(self):
        r = self.win.remote
        on = bool(r and r.running)
        if self.on.isChecked() != on:
            self.on.blockSignals(True)
            self.on.setChecked(on)
            self.on.blockSignals(False)
        for w in (self.qr, self.how, self.code_btn, self.code, self.code_left, self.list, self.forget_btn, self.reset_btn):
            w.setEnabled(on)
        if not on:
            self.hint.setText(_("Увімкніть — і керуйте Платівкою з телефона в тій самій Wi-Fi-мережі: "
                                "пауза, наступний трек, гучність, таймер сну. Нічого встановлювати не треба."))
            self.qr.clear()
            self._qr_for = None
            self.how.setText("")
            self.code.setText("")
            self.code_left.setText("")
            self.list.clear()
            return
        self.hint.setText(_("Наведіть камеру телефона на QR-код і відкрийте посилання. "
                            "Телефон запам'ятає підключення — наступного разу просто відкрийте сторінку."))
        url = r.pair_url()
        if url != self._qr_for:
            self._qr_for = url
            self.qr.setPixmap(qr_pixmap(url, 176))
        self.how.setText(_("Або відкрийте на телефоні адресу\n{url}\nі натисніть «Показати код».").format(url=r.base_url()))
        left = r.code_left()
        shown = bool(left and r.code)
        self.code.setText(f"{r.code[:3]} {r.code[3:]}" if shown else "")
        self.code_left.setText(_("діє ще {t}").format(t=fmt_time(left)) if shown else "")
        devs = r.devices
        ids = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if ids != [d["id"] for d in devs] or not devs:
            cur = self.list.currentRow()
            self.list.clear()
            for d in devs:
                ago = max(0, int(time.time()) - int(d.get("seen", 0)))
                when = _("щойно") if ago < 90 else _("{n} хв тому").format(n=ago // 60) if ago < 3600 \
                    else _("{n} год тому").format(n=ago // 3600) if ago < 86400 else _("{n} дн тому").format(n=ago // 86400)
                it = QListWidgetItem(f"{d.get('name', '?')}   ·   {when}")
                it.setData(Qt.UserRole, d["id"])
                self.list.addItem(it)
            if not devs:
                it = QListWidgetItem(_("Поки жодного"))
                it.setFlags(Qt.NoItemFlags)
                self.list.addItem(it)
            self.list.setCurrentRow(min(cur, self.list.count() - 1))
        self.forget_btn.setEnabled(bool(devs))
        self.reset_btn.setEnabled(bool(devs))


def qr_pixmap(text: str, size: int) -> QPixmap:
    """QR-код як картинка (чорне на білому, з полем — так його читає будь-яка камера)."""
    import segno
    m = segno.make(text, error="m").matrix
    n = len(m) + 8
    k = max(1, size // n)
    img = QImage(n * k, n * k, QImage.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    for y, row in enumerate(m):
        for x, v in enumerate(row):
            if v:
                p.fillRect((x + 4) * k, (y + 4) * k, k, k, QColor("black"))
    p.end()
    return QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)


class CopyDialog(QDialog):
    """«Копіювати на флешку»: спершу показати розмір і вільне місце, нічого не перезаписувати без дозволу."""

    def __init__(self, win: "MainWindow", paths: list[str], dest: str):
        super().__init__(win)
        self.win, self.paths, self.dest = win, paths, dest
        self.setWindowTitle(_("Копіювати на флешку"))
        self.resize(480, 300)
        lay = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.summary)
        self.numbered = QCheckBox(_("Нумерувати файли (01, 02…) — щоб магнітола грала по порядку"))
        self.numbered.setChecked(True)
        self.numbered.toggled.connect(self.refresh)
        lay.addWidget(self.numbered)
        self.exist = QLabel()
        self.exist.setWordWrap(True)
        lay.addWidget(self.exist)
        self.r_skip = QRadioButton(_("Пропустити наявні"))
        self.r_repl = QRadioButton(_("Замінити наявні"))
        self.r_skip.setChecked(True)
        lay.addWidget(self.r_skip)
        lay.addWidget(self.r_repl)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("dim")
        lay.addWidget(self.note)
        from PySide6.QtWidgets import QProgressBar
        self.bar = QProgressBar()
        self.bar.hide()
        lay.addWidget(self.bar)
        lay.addStretch()
        bb = QDialogButtonBox()
        self.go = bb.addButton(_("Копіювати"), QDialogButtonBox.AcceptRole)
        self.cancel_btn = bb.addButton(_("Скасувати"), QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.run)
        bb.rejected.connect(self._cancel)
        lay.addWidget(bb)
        self._stop = False
        self._state = None
        self.refresh()

    def refresh(self, *_a):
        from .export import plan_copy
        from .favorites import fmt_size
        self.plan = plan = plan_copy(self.paths, self.win.track, self.dest, self.numbered.isChecked())
        free = _(" Вільно: {free}.").format(free=fmt_size(plan.free)) if plan.free is not None else ""
        self.summary.setText(_("Файлів: {n} ({size}) → {dest}.").format(
            n=len(plan.items), size=fmt_size(plan.total), dest=self.dest) + free)
        k = len(plan.existing)
        self.exist.setText(_("Уже є в цій теці: {n}.").format(n=k) if k else "")
        for w in (self.exist, self.r_skip, self.r_repl):
            w.setVisible(bool(k))
        if not plan.fits:
            self.note.setText(_("Не вміститься: бракує {size}. Приберіть частину треків зі списку або візьміть більшу флешку.")
                              .format(size=fmt_size(plan.total - plan.free)))
        else:
            self.note.setText(_("Оригінали лишаються на місці. Альбоми одним файлом із .cue копіюються цілим файлом."))
        self.go.setEnabled(plan.fits and bool(plan.items))

    def run(self):
        from .export import run_copy
        self.go.setEnabled(False)
        for w in (self.numbered, self.r_skip, self.r_repl):
            w.setEnabled(False)
        self.bar.setRange(0, len(self.plan.items))
        self.bar.setValue(0)
        self.bar.show()
        replace = self.r_repl.isChecked()
        state = self._state = {"i": 0, "res": None}

        def progress(i, n, name):
            state["i"] = i

        def work():
            try:
                state["res"] = run_copy(self.plan, replace, progress, lambda: self._stop)
            except OSError as e:
                state["res"] = (0, 0, [str(e)])
        threading.Thread(target=work, daemon=True).start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(150)

    def _poll(self):
        st = self._state
        self.bar.setValue(st["i"])
        if st["res"] is None:
            return
        self._timer.stop()
        done, skipped, errors = st["res"]
        msg = _("Скопійовано: {n}").format(n=n_tracks(done))
        if skipped:
            msg += " · " + _("пропущено наявних: {n}").format(n=skipped)
        if errors:
            msg += " · " + _("помилок: {n}").format(n=len(errors))
            QMessageBox.warning(self, _("Копіювати на флешку"), msg + "\n\n" + "\n".join(errors[:15]))
        self.win.toast(msg)
        self.accept()

    def _cancel(self):
        if self._state and self._state["res"] is None:
            self._stop = True                     # дочекаємося поточного файлу — і стоп
            self.cancel_btn.setEnabled(False)
            return
        self.reject()

    def closeEvent(self, e):
        if self._state and self._state["res"] is None:
            self._stop = True
            e.ignore()
            return
        super().closeEvent(e)


class RemoveUnlikedDialog(QDialog):
    """«Прибрати неулюблені»: лише зі списку (типово) або ще й файли в Кошик — ніколи назавжди."""

    def __init__(self, win: "MainWindow", paths: list[str], where: str):
        super().__init__(win)
        self.win, self.paths, self.where = win, paths, where
        self.setWindowTitle(_("Прибрати неулюблені"))
        self.resize(500, 420)
        lay = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.r_list = QRadioButton(_("Лише зі списку — файли лишаться на диску"))
        self.r_disk = QRadioButton()
        self.r_list.setChecked(True)
        for r in (self.r_list, self.r_disk):
            r.toggled.connect(self.refresh)
            lay.addWidget(r)
        self.only_heard = QCheckBox(_("Не чіпати треки, які ще не звучали"))
        self.only_heard.setChecked(True)
        self.only_heard.toggled.connect(self.refresh)
        lay.addWidget(self.only_heard)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("dim")
        lay.addWidget(self.note)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        bb = QDialogButtonBox()
        self.go = bb.addButton("", QDialogButtonBox.AcceptRole)
        bb.addButton(_("Скасувати"), QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.run)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.refresh()

    def refresh(self, *_a):
        from .favorites import fmt_size, removal_plan
        self.plan = plan = removal_plan(self.paths, self.win.favs, self.win.hist, self.only_heard.isChecked())
        n = len(plan["remove"])
        self.summary.setText(_("{where}: {total}, з них ♥ {fav} улюблених. Прибрати: {n}.").format(
            where=self.where, total=n_tracks(plan["total"]), fav=plan["favorites"], n=n_tracks(n)))
        self.r_disk.setText(_("Зі списку й з диска — {n} ({size}) у Кошик").format(
            n=n_tracks(len(plan["files"])), size=fmt_size(plan["size"])))
        notes = []
        if plan["unheard"] and self.only_heard.isChecked():
            notes.append(_("Ще не звучали й лишаться: {n}.").format(n=n_tracks(plan["unheard"])))
        if plan["cue"] and self.r_disk.isChecked():
            notes.append(_("Альбоми одним файлом із .cue з диска не прибираються (один файл — увесь альбом): {n}.")
                         .format(n=n_tracks(plan["cue"])))
        if self.r_disk.isChecked():
            notes.append(_("Файли йдуть у Кошик — їх можна відновити."))
        self.note.setText(" ".join(notes))
        self.list.clear()
        for p in plan["remove"][:500]:
            self.list.addItem(self.win.track(p).display)
        self.go.setText(_("Перемістити в Кошик") if self.r_disk.isChecked() else _("Прибрати зі списку"))
        self.go.setEnabled(n > 0)

    def run(self):
        from .favorites import move_to_trash
        plan = self.plan
        gone = set(plan["remove"])
        trashed, failed = [], []
        if self.r_disk.isChecked() and plan["files"]:
            trashed, failed = move_to_trash(plan["files"])
            gone = set(plan["remove"]) - set(failed)
            for p in trashed:
                self.win.lib.tracks.pop(p, None)
            self.win.lib.save()
        self.win.drop_from_playlist(gone)
        self.win.rebuild_tree()
        if self.r_disk.isChecked():
            msg = _("У Кошику: {n}").format(n=n_tracks(len(trashed)))
            if failed:
                msg += " · " + _("не вдалося: {n}").format(n=len(failed))
        else:
            msg = _("Прибрано зі списку: {n}").format(n=n_tracks(len(gone)))
        self.win.toast(msg)
        self.accept()


class DuplicatesDialog(QDialog):
    """«Знайти дублікати»: групи однакових треків, галочка — яку копію лишити.
    Типово зайві прибираються лише зі списку; файли — тільки в Кошик і тільки якщо попросити."""

    def __init__(self, win: "MainWindow"):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(_("Дублікати"))
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        self.summary = QLabel(_("Шукаю дублікати…"))
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Трек / файл"), _("Якість")])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.itemChanged.connect(self._changed)
        lay.addWidget(self.tree, 1)
        self.r_list = QRadioButton(_("Лише зі списку відтворення — файли лишаться на диску"))
        self.r_disk = QRadioButton()
        self.r_list.setChecked(True)
        for r in (self.r_list, self.r_disk):
            r.toggled.connect(self.refresh)
            lay.addWidget(r)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("dim")
        lay.addWidget(self.note)
        bb = QDialogButtonBox()
        self.go = bb.addButton(_("Прибрати зайві"), QDialogButtonBox.AcceptRole)
        bb.addButton(_("Закрити"), QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.run)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.groups = None
        self._stop = False
        self.go.setEnabled(False)
        for r in (self.r_list, self.r_disk):
            r.setEnabled(False)
        tracks = dict(win.lib.tracks)
        for p in win.playlist:
            if p not in tracks:
                tracks[p] = win.track(p)
        state = self._state = {"i": 0, "n": 0, "res": None}

        def work():
            from .dupes import find_duplicates

            def prog(i, n):
                state["i"], state["n"] = i, n
            state["res"] = find_duplicates(tracks.values(), win.favs, win.hist, prog, lambda: self._stop)
        threading.Thread(target=work, daemon=True).start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(200)
        self.finished.connect(lambda *_: setattr(self, "_stop", True))

    def _poll(self):
        st = self._state
        if st["res"] is None:
            if st["n"]:
                self.summary.setText(_("Шукаю дублікати… порівнюю файли: {i} з {n}").format(i=st["i"], n=st["n"]))
            return
        self._timer.stop()
        self.groups = st["res"]
        self._fill()

    def _detail(self, path: str) -> str:
        from .favorites import fmt_size
        t = self.win.track(path)
        bits = [t.fmt]
        if t.bitrate:
            bits.append(f"{t.bitrate} kbps")
        try:
            bits.append(fmt_size(os.path.getsize(path)))
        except OSError:
            pass
        if self.win.is_fav(path):
            bits.append("♥")
        n = self.win.hist.plays(path)
        if n:
            bits.append(_("слухали {n}×").format(n=n))
        return " · ".join(bits)

    def _fill(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        for gi, g in enumerate(self.groups):
            t = self.win.track(g.paths[0])
            head = QTreeWidgetItem(self.tree, [("≡ " if g.kind == "file" else "≈ ") + t.display,
                                               _("однакові файли") if g.kind == "file" else _("та сама пісня")])
            f = head.font(0)
            f.setBold(True)
            head.setFont(0, f)
            head.setFlags(Qt.ItemIsEnabled)
            head.setFirstColumnSpanned(False)
            for p in g.paths:
                it = QTreeWidgetItem(self.tree, ["    " + p, self._detail(p)])
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                it.setCheckState(0, Qt.Checked if p in g.keep else Qt.Unchecked)
                it.setToolTip(0, _("Галочка — цю копію лишити"))
                it.setData(0, Qt.UserRole, (gi, p))
        self.tree.blockSignals(False)
        for r in (self.r_list, self.r_disk):
            r.setEnabled(bool(self.groups))
        self.refresh()

    def _changed(self, it, col):
        data = it.data(0, Qt.UserRole)
        if not data:
            return
        gi, p = data
        g = self.groups[gi]
        if it.checkState(0) == Qt.Checked:
            g.keep.add(p)
        else:
            g.keep.discard(p)
            if not g.keep:                        # хоч одна копія лишається завжди
                self.tree.blockSignals(True)
                it.setCheckState(0, Qt.Checked)
                self.tree.blockSignals(False)
                g.keep.add(p)
                self.win.toast(_("Хоча б одну копію треба лишити"))
        self.refresh()

    def refresh(self, *_a):
        from .dupes import total_size
        from .favorites import fmt_size
        if self.groups is None:
            return
        extra = [p for g in self.groups for p in g.extra]
        in_pl = [p for p in extra if p in set(self.win.playlist)]
        files = [p for p in extra if not p.startswith("demo:")]
        if not self.groups:
            self.summary.setText(_("Дублікатів не знайдено."))
        else:
            self.summary.setText(_("Груп: {g}. Зайвих копій: {n}. Галочкою позначено, яку копію лишити — "
                                   "типово найкращу: улюблену, без втрат, з вищим бітрейтом.").format(
                g=len(self.groups), n=len(extra)))
        self.r_disk.setText(_("Зайві файли — у Кошик: {n} ({size})").format(
            n=n_tracks(len(files)), size=fmt_size(total_size(files))))
        if self.r_disk.isChecked():
            self.note.setText(_("Файли йдуть у Кошик — їх можна відновити."))
            self.go.setText(_("Перемістити в Кошик"))
            self.go.setEnabled(bool(files))
        else:
            self.note.setText(_("У списку відтворення з них: {n}.").format(n=len(in_pl)) if extra else "")
            self.go.setText(_("Прибрати зі списку"))
            self.go.setEnabled(bool(in_pl))

    def run(self):
        from .favorites import move_to_trash
        extra = {p for g in self.groups for p in g.extra}
        if self.r_disk.isChecked():
            trashed, failed = move_to_trash(sorted(extra))
            for p in trashed:
                self.win.lib.tracks.pop(p, None)
            self.win.lib.save()
            self.win.drop_from_playlist(set(trashed))
            self.win.rebuild_tree()
            msg = _("У Кошику: {n}").format(n=n_tracks(len(trashed)))
            if failed:
                msg += " · " + _("не вдалося: {n}").format(n=len(failed))
        else:
            gone = extra & set(self.win.playlist)
            self.win.drop_from_playlist(gone)
            msg = _("Прибрано зі списку: {n}").format(n=n_tracks(len(gone)))
        self.win.toast(msg)
        self.accept()


class CoverPickDialog(QDialog):
    """«Знайти обкладинку…»: до шести варіантів з MusicBrainz та Apple — людина обирає сама."""

    def __init__(self, win: "MainWindow", path: str):
        super().__init__(win)
        self.win, self.path = win, path
        self.t = t = win.track(path)
        self.setWindowTitle(_("Знайти обкладинку"))
        self.resize(560, 470)
        lay = QVBoxLayout(self)
        what = f"{t.albumartist or t.artist} — {t.album or t.title}"
        self.head = QLabel(_("Шукаю: {what}…").format(what=what))
        self.head.setWordWrap(True)
        lay.addWidget(self.head)
        from PySide6.QtWidgets import QGridLayout
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        lay.addLayout(self.grid)
        lay.addStretch()
        self.folder = QCheckBox(_("Також зберегти як cover.jpg у теку з музикою"))
        lay.addWidget(self.folder)
        note = QLabel(_("Надсилається лише виконавець і назва альбому. Обрана обкладинка зберігається "
                        "в кеші Платівки й далі працює без інтернету. Файли з музикою не змінюються."))
        note.setWordWrap(True)
        note.setObjectName("dim")
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(_("Закрити"))
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._alive = True
        self.finished.connect(lambda *_: setattr(self, "_alive", False))
        threading.Thread(target=self._search, daemon=True).start()

    def _search(self):
        from . import covers
        cands = covers.candidates(self.t)
        thumbs = []
        for c in cands:
            if not self._alive:
                return
            thumbs.append((c, covers.download(c["thumb"])))
        self.win.call_from_thread(self._show, thumbs)

    def _show(self, thumbs):
        if not self._alive:
            return
        shown = 0
        for c, data in thumbs:
            if not data:
                continue
            img = QImage.fromData(data)
            if img.isNull():
                continue
            b = QToolButton()
            b.setIcon(QIcon(QPixmap.fromImage(img)))
            b.setIconSize(QSize(150, 150))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            fm = QFontMetrics(b.font())
            b.setText(fm.elidedText(c["label"], Qt.ElideRight, 150) + "\n" + c["src"])
            b.setToolTip(c["label"])
            b.setAutoRaise(True)
            b.clicked.connect(lambda _c=False, url=c["url"]: self._choose(url))
            self.grid.addWidget(b, shown // 3, shown % 3)
            shown += 1
        self.head.setText(_("Оберіть обкладинку:") if shown else
                          _("Нічого не знайшлося. Перевірте назву альбому й виконавця в тегах файлу або підключення до інтернету."))

    def _choose(self, url: str):
        from . import covers
        self.head.setText(_("Завантажую…"))
        for i in range(self.grid.count()):
            self.grid.itemAt(i).widget().setEnabled(False)
        folder = self.folder.isChecked()

        def work():
            data = covers.download(url)
            jpg = covers.store(self.t, data, folder) if data else None
            self.win.call_from_thread(self._done, bool(jpg))
        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok: bool):
        if ok:
            self.win._online_cover_ready(self.path)
            self.win.toast(_("Обкладинку збережено"))
            self.accept()
        else:
            self.head.setText(_("Не вдалося завантажити — спробуйте інший варіант."))
            for i in range(self.grid.count()):
                self.grid.itemAt(i).widget().setEnabled(True)


class FoldersDialog(QDialog):
    """Теки медіатеки: позначити й прибрати, прибрати всі, додати ще."""

    def __init__(self, win: "MainWindow"):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(_("Теки медіатеки"))
        self.resize(560, 380)
        lay = QVBoxLayout(self)
        hint = QLabel(_("Позначте теки й натисніть «Прибрати позначені». Файли на диску залишаться."))
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        add = QPushButton(_("+ Додати…"))
        add.clicked.connect(self._add)
        rm = QPushButton(_("Прибрати позначені"))
        rm.clicked.connect(self._remove)
        self.rm_all = QPushButton(_("Прибрати всі"))
        self.rm_all.clicked.connect(self._remove_all)
        row.addWidget(add)
        row.addStretch()
        row.addWidget(rm)
        row.addWidget(self.rm_all)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.Close).setText(_("Закрити"))
        lay.addWidget(bb)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for f in self.win.lib.folders:
            n = len(self.win.lib.under(f))
            it = QListWidgetItem(f"{Path(f).name or f}   ·   {n_tracks(n)}\n{f}")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, f)
            self.list.addItem(it)
        self.rm_all.setVisible(len(self.win.lib.folders) > 1)

    def _add(self):
        self.win.add_library_folder()
        self.refresh()

    def _remove(self):
        paths = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                 if self.list.item(i).checkState() == Qt.Checked]
        if not paths and self.list.currentItem() is not None:
            paths = [self.list.currentItem().data(Qt.UserRole)]
        if paths:
            self.win.remove_folders(paths)
            self.refresh()

    def _remove_all(self):
        r = QMessageBox.question(self, _("Прибрати всі теки?"),
                                 _("Медіатека стане порожньою. Файли на диску й список відтворення залишаться."))
        if r == QMessageBox.Yes:
            self.win.remove_folders(list(self.win.lib.folders))
            self.refresh()


# ═══════════════════════════════ платформа ═══════════════════════════════
def apply_mica(widget: QWidget, dark: bool) -> bool:
    """Windows 11: напівпрозорий фон Mica під усім вікном. False — системою не підтримується."""
    if not sysdeps.IS_WIN or os.environ.get("PLATIVKA_NO_MICA"):
        return False
    try:
        import ctypes
        if sys.getwindowsversion().build < 22000:
            return False
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi

        class MARGINS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(-1, -1, -1, -1)))
        val = ctypes.c_int(1 if dark else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), 4)       # темний заголовок
        backdrop = ctypes.c_int(2)                                        # 2 = Mica
        r = dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), 4)
        return r == 0
    except Exception as e:
        log(f"mica: {e}")
        return False


class Bridge(QObject):
    """Виклики з інших потоків (гучність системи, трей Windows, SMTC) — у потік вікна."""
    call = Signal(object)

    def __init__(self):
        super().__init__()
        self.call.connect(lambda fn: fn())


# ═══════════════════════════════ головне вікно ═══════════════════════════════
class MainWindow(QMainWindow, PlayerExtras, RemoteHost):
    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo
        self.cfg = self.load_cfg()
        self.lib = Library(self.cfg.get("folders", []))
        self.extra: dict[str, Track] = {}
        self.playlist: list[str] = [p for p in self.cfg.get("playlist", []) if isinstance(p, str)]
        self.current: int = int(self.cfg.get("current", -1))
        self.player_volume = int(self.cfg.get("volume", 70))
        self.volume = self.player_volume
        self.volume_mode = self.cfg.get("volume_mode", "system")
        self.sysvol = None
        self.sys_muted = False
        self._sysvol_t = 0.0
        self.shuffle = bool(self.cfg.get("shuffle", False))
        self.repeat = self.cfg.get("repeat", "off")
        self.popups = bool(self.cfg.get("popups", True))
        self.replaygain = self.cfg.get("replaygain", "album")
        self.check_updates = bool(self.cfg.get("check_updates", True))
        self.online_covers = bool(self.cfg.get("online_covers", False))
        self.cover_rev = 0
        self.update_info = None
        self.remote = None              # пульт з телефона (RemoteServer), коли увімкнено
        self.remote_cfg = self.cfg.setdefault("remote", {})
        self.base = self.cfg.get("theme", "auto")
        self.skin = self.cfg.get("skin") if self.cfg.get("skin") in skins.SKINS else "classic"
        self.vibrancy = False
        self.view = self.cfg.get("view", "full") if self.cfg.get("view") in ("full", "compact") else "full"
        self.collapsed = bool(self.cfg.get("collapsed", False))
        self.on_top = bool(self.cfg.get("on_top", False))
        self.lib_mode = self.cfg.get("lib_mode", "artists")
        self.tab = self.cfg.get("tab", "playlist")
        self.remaining = bool(self.cfg.get("remaining", False))
        self.minimize_to_tray = bool(self.cfg.get("minimize_to_tray", False))
        self.history: list[int] = []
        self.stopped = True
        self.accent_rgb = DEFAULT_ACCENT
        self.cover_pix: QPixmap | None = None
        self._cover_path = None
        self._cover_file: Path | None = None
        self.player = None
        self.scanning = False
        self._load_lock = asyncio.Lock()
        self._load_gen = 0
        self._quitting = False
        self._expanded_h = int(self.cfg.get("expanded_h", 720))
        self.mica = False
        self.bridge = Bridge()
        self.mpris = None
        self.smtc = None
        self.tray = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        # Mica (Windows 11): прозорість треба увімкнути ще до створення вікна системою
        self._want_mica = (sysdeps.IS_WIN and not os.environ.get("PLATIVKA_NO_MICA")
                           and sys.getwindowsversion().build >= 22000)
        if self._want_mica:
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
        # macOS: прозорість вмикається одразу — тоді скін «macOS» перемикається без перезапуску;
        # в інших скінах фон усе одно суцільний
        if skins.vibrancy_supported():
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAcceptDrops(True)
        self.build_ui()
        self.build_actions()
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().hide()
        self.apply_theme()
        g = self.cfg.get("geometry")
        if isinstance(g, list) and len(g) == 4:
            self.setGeometry(*g)
        else:
            self.resize(520, 640)
        self.apply_view(initial=True)
        self.rebuild_playlist()
        self.rebuild_tree()
        self.update_flags()
        self.update_now_playing()
        if self.on_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

    # ───────────── конфіг ─────────────
    def load_cfg(self) -> dict:
        d = {"folders": [], "playlist": [], "current": -1, "position": 0.0, "volume": 70}
        for f in (CFG_FILE, CONF_DIR / "config.json"):  # уперше — медіатека з консольної версії
            try:
                data = json.loads(f.read_text("utf-8"))
            except Exception:
                continue
            if f != CFG_FILE:
                data = {k: data[k] for k in ("folders", "playlist", "current", "volume", "shuffle", "repeat",
                                             "lib_mode", "volume_mode") if k in data}
            d.update(data)
            break
        return d

    def save_cfg(self):
        pos = self.player.time_pos if self.player and self.player.active else self.cfg.get("position", 0)
        g = self.normalGeometry() if not self.collapsed else self.geometry()
        self.cfg.update(folders=self.lib.folders, playlist=self.playlist, current=self.current,
                        position=round(pos or 0, 1), volume=self.player_volume, volume_mode=self.volume_mode,
                        shuffle=self.shuffle, repeat=self.repeat, popups=self.popups, theme=self.base,
                        skin=self.skin, view=self.view, collapsed=self.collapsed, on_top=self.on_top, lib_mode=self.lib_mode,
                        tab=self.tab, remaining=self.remaining, expanded_h=self._expanded_h,
                        minimize_to_tray=self.minimize_to_tray, replaygain=self.replaygain,
                        check_updates=self.check_updates, online_covers=self.online_covers,
                        geometry=[g.x(), g.y(), g.width(), g.height()])
        try:
            CONF_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CFG_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=1), "utf-8")
            tmp.replace(CFG_FILE)
        except OSError:
            pass

    # ───────────── інтерфейс ─────────────
    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        self._outer = outer
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # ── картка плеєра ──
        self.card = QFrame()
        self.card.setObjectName("card")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(10, 10, 10, 8)
        cl.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(12)
        self.cover = CoverLabel(128)
        self.cover.clicked.connect(self.toggle_view)
        top.addWidget(self.cover, 0, Qt.AlignTop)

        self.lcd = QFrame()
        self.lcd.setObjectName("lcd")
        lv = QVBoxLayout(self.lcd)
        lv.setContentsMargins(10, 6, 10, 6)
        lv.setSpacing(2)
        r1 = QHBoxLayout()
        self.state = QLabel("■")
        self.state.setObjectName("state")
        self.state.setFixedWidth(18)
        r1.addWidget(self.state)
        self.clock = LcdClock()
        self.clock.clicked.connect(self.toggle_remaining)
        r1.addWidget(self.clock, 1)
        self.vu = LevelBars(14, 7)
        self.vu.setFixedSize(112, 44)
        r1.addWidget(self.vu, 0, Qt.AlignVCenter)
        lv.addLayout(r1)
        self._lcd_gap = QSpacerItem(0, 6)
        lv.addSpacerItem(self._lcd_gap)
        # компактний вигляд: замість табло — назва великим шрифтом і рядок виконавця
        self.c_title = QLabel()
        self.c_title.setObjectName("bigtitle")
        self.c_sub = ElidedLabel()
        self.c_sub.setObjectName("sub")
        self.title = QLabel()
        self.title.setObjectName("title")
        self.title.setTextFormat(Qt.RichText)     # ♥ кольором, лише якщо трек в улюблених
        self.c_title.setTextFormat(Qt.RichText)
        self.info = QLabel()
        self.info.setObjectName("dim")
        for w in (self.c_title, self.c_sub, self.title, self.info):
            w.setMinimumWidth(10)
            w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            lv.addWidget(w)
        self.flagw = QWidget()
        flags = QHBoxLayout(self.flagw)
        flags.setContentsMargins(0, 0, 0, 0)
        flags.setSpacing(14)
        self._flags_l = flags
        # іконки-перемикачі (скіни macOS і Windows, а також компактний вигляд у будь-якому скіні)
        self.icon_flags = {}
        for key, fn in (("shuffle", self.toggle_shuffle), ("repeat", self.cycle_repeat),
                        ("popups", self.toggle_popups), ("remote", self.open_remote)):
            b = QToolButton()
            b.setObjectName("flagicon")
            b.setCursor(Qt.PointingHandCursor)
            b.setIconSize(QSize(14, 14))
            b.clicked.connect(fn)
            self.icon_flags[key] = b
            flags.addWidget(b)
        self.f_shuffle = Clickable()
        self.f_shuffle.clicked.connect(self.toggle_shuffle)
        self.f_repeat = Clickable()
        self.f_repeat.clicked.connect(self.cycle_repeat)
        self.f_popups = Clickable()
        self.f_popups.clicked.connect(self.toggle_popups)
        self.f_sleep = Clickable()          # таймер сну: видно, лише коли увімкнено; клік — вимкнути
        self.f_sleep.setObjectName("flagon")
        self.f_sleep.clicked.connect(lambda: self.choose_sleep(None))
        self.f_sleep.hide()
        self.f_remote = Clickable()         # пульт увімкнено: клік — вікно пульта
        self.f_remote.setObjectName("flagon")
        self.f_remote.clicked.connect(self.open_remote)
        self.f_remote.hide()
        self.f_update = Clickable()         # «вийшла нова версія»: клік — сторінка завантаження
        self.f_update.setObjectName("flagon")
        self.f_update.clicked.connect(self.open_update)
        self.f_update.hide()
        for w in (self.f_shuffle, self.f_repeat, self.f_popups, self.f_sleep, self.f_remote, self.f_update):
            flags.addWidget(w)
        flags.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lv.addWidget(self.flagw)
        top.addWidget(self.lcd, 1)
        self.mini_vu = LevelBars(12, 6)          # більше не показується: у компактному вигляді місце — назві
        self.mini_vu.setFixedSize(92, 40)
        self.mini_vu.hide()
        self.tcl = QHBoxLayout()                 # компактний вигляд: кнопки в одному ряду з назвою
        self.tcl.setSpacing(4)
        top.addLayout(self.tcl)
        self.top_row = top
        cl.addLayout(top)

        sr = QHBoxLayout()
        sr.setSpacing(6)
        self.sr = sr
        self.pos_lbl = QLabel("-:--")             # компактний вигляд: поточний час ліворуч від смуги
        self.pos_lbl.setObjectName("dim")
        self.seek = SeekSlider()
        self.seek.setFixedHeight(16)
        self.seek.seek.connect(lambda f: self.spawn(self.seek_frac(f)))
        sr.addWidget(self.seek, 1)
        self.time = QLabel("-:--")
        self.time.setObjectName("dim")
        sr.addWidget(self.time)
        cl.addLayout(sr)

        tr = QHBoxLayout()
        tr.setSpacing(5)
        self.tr = tr
        self.buttons = {}
        for key, glyph, tip, fn in (
                ("prev", "prev", _("Попередній трек"), lambda: self.spawn(self.prev())),
                ("toggle", "play", _("Грати / пауза"), lambda: self.spawn(self.toggle())),
                ("play", "play", _("Грати"), lambda: self.spawn(self.play())),
                ("pause", "pause", _("Пауза"), lambda: self.spawn(self.pause())),
                ("stop", "stop", _("Стоп"), lambda: self.spawn(self.stop())),
                ("next", "next", _("Наступний трек"), lambda: self.spawn(self.next())),
                ("eject", "eject", _("Додати теку до списку"), self.add_playlist_folder)):
            b = QToolButton()
            b.setProperty("glyph", glyph)
            b.setIconSize(QSize(12, 12))
            b.setFixedSize(30, 22)
            b.setToolTip(tip)
            b.setObjectName("tbtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            self.buttons[key] = b
            tr.addWidget(b)
        tr.addStretch()
        self.pin = QToolButton()
        self.pin.setProperty("glyph", "pin")
        self.pin.setIconSize(QSize(12, 12))
        self.pin.setFixedSize(26, 22)
        self.pin.setToolTip(_("Поверх усіх вікон"))
        self.pin.setObjectName("tbtn")
        self.pin.setCheckable(True)
        self.pin.setChecked(self.on_top)
        self.pin.clicked.connect(self.toggle_on_top)
        tr.addWidget(self.pin)
        self.collapse_btn = QToolButton()
        self.collapse_btn.setIconSize(QSize(12, 12))
        self.collapse_btn.setFixedSize(26, 22)
        self.collapse_btn.setObjectName("tbtn")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self.toggle_collapsed)
        tr.addWidget(self.collapse_btn)
        self.vol_icon = QToolButton()
        self.vol_icon.setObjectName("plain")
        self.vol_icon.setIconSize(QSize(14, 14))
        self.vol_icon.setToolTip(_("Гучність"))
        self.vol_icon.clicked.connect(self._vol_icon_clicked)
        self.vol_label = Clickable(_("гучн"))
        self.vol_label.setObjectName("dim")
        self.vol_label.setToolTip(_("Гучність:") + " " + _("як у системі (клавіші гучності керують і плеєром)"))
        tr.addSpacing(6)
        tr.addWidget(self.vol_label)
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.setFixedWidth(90)
        self.vol.setFixedHeight(16)
        self.vol.setValue(self.volume)
        self.vol.valueChanged.connect(self._vol_moved)
        tr.addWidget(self.vol)
        self.vol_pct = QLabel()
        self.vol_pct.setObjectName("dim")
        self.vol_pct.setFixedWidth(36)
        self.vol_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        tr.addWidget(self.vol_pct)
        cl.addLayout(tr)
        outer.addWidget(self.card)
        self._card_widgets = [self.seek, self.time, self.pos_lbl, self.pin, self.collapse_btn, self.vol_icon,
                              self.vol_label, self.vol, self.vol_pct] + list(self.buttons.values())

        # ── список і медіатека ──
        self.lists = QFrame()
        self.lists.setObjectName("listcard")
        ll = QVBoxLayout(self.lists)
        ll.setContentsMargins(8, 6, 8, 6)
        ll.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(4)
        self.tab_pl = QPushButton(_("Список відтворення"))
        self.tab_lib = QPushButton(_("Медіатека"))
        self.seg = QFrame()
        self.seg.setObjectName("seg")
        sl = QHBoxLayout(self.seg)
        sl.setContentsMargins(2, 2, 2, 2)
        sl.setSpacing(2)
        for b, t in ((self.tab_pl, "playlist"), (self.tab_lib, "library")):
            b.setObjectName("tab")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, t=t: self.set_tab(t))
            sl.addWidget(b)
        head.addWidget(self.seg)
        head.addSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Знайти…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.apply_filter)
        self.search.returnPressed.connect(self.search_enter)
        head.addWidget(self.search, 1)
        self.menu_btn = QToolButton()
        self.menu_btn.setProperty("glyph", "menu")
        self.menu_btn.setIconSize(QSize(12, 12))
        self.menu_btn.setFixedSize(26, 22)
        self.menu_btn.setObjectName("tbtn")
        self.menu_btn.setPopupMode(QToolButton.InstantPopup)
        head.addWidget(self.menu_btn)
        ll.addLayout(head)

        self.stack = QStackedWidget()
        # список відтворення
        pl = QWidget()
        pv = QVBoxLayout(pl)
        pv.setContentsMargins(0, 0, 0, 0)
        self.table = TrackTable()
        self.table.setItemDelegate(CurrentMark(self))
        self.table.activated_row.connect(lambda r: self.spawn(self.play_index(r)))
        self.table.delete_pressed.connect(self.remove_selected)
        self.table.hover_changed.connect(lambda a, b: [self._heart_cell(r) for r in (a, b)])
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: [self._heart_cell(x) for x in (pr, r)])
        self.table.cellClicked.connect(lambda r, c: self._like_row(r) if c == 3 else None)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_menu)
        pv.addWidget(self.table, 1)
        self.pl_empty = QLabel(_("Список порожній.\n\nОберіть альбом чи теку в медіатеці й натисніть Enter або P, "
                                 "або додайте теку кнопкою «+ Тека» нижче."))
        self.pl_empty.setObjectName("empty")
        self.pl_empty.setAlignment(Qt.AlignCenter)
        self.pl_empty.setWordWrap(True)
        pv.addWidget(self.pl_empty, 1)
        pb = QHBoxLayout()
        for t, fn in ((_(" + Тека "), self.add_playlist_folder), (_(" − Прибрати "), self.remove_selected),
                      (_(" Очистити "), self.clear_playlist)):
            b = QPushButton(t.strip())
            b.setObjectName("small")
            b.clicked.connect(fn)
            pb.addWidget(b)
        pb.addStretch()
        self.pl_count = QLabel()
        self.pl_count.setObjectName("dim")
        pb.addWidget(self.pl_count)
        pv.addLayout(pb)
        self.stack.addWidget(pl)
        # медіатека
        lb = QWidget()
        lbv = QVBoxLayout(lb)
        lbv.setContentsMargins(0, 0, 0, 0)
        modes = QHBoxLayout()
        self.mode_art = QPushButton(_("Виконавці"))
        self.mode_dir = QPushButton(_("Теки"))
        for b, m in ((self.mode_art, "artists"), (self.mode_dir, "folders")):
            b.setObjectName("mode")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, m=m: self.set_lib_mode(m))
            modes.addWidget(b)
        modes.addStretch()
        lbv.addLayout(modes)
        self.tree = LibraryTree()
        self.tree.activated_item.connect(self.lib_activate)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        lbv.addWidget(self.tree, 1)
        self.lib_empty = QLabel(_("Медіатека порожня.\n\nДодайте теку з музикою кнопкою «+ Тека» "
                                  "або просто перетягніть теку у вікно."))
        self.lib_empty.setObjectName("empty")
        self.lib_empty.setAlignment(Qt.AlignCenter)
        self.lib_empty.setWordWrap(True)
        lbv.addWidget(self.lib_empty, 1)
        lbb = QHBoxLayout()
        for t, fn, name in ((_(" + Тека "), self.add_library_folder, "small"),
                            (_(" Теки… "), self.manage_folders, "small"),
                            (_(" ▶ Усе "), self.lib_all, "primary"), (" ↻ ", self.start_scan, "small")):
            b = QPushButton(t.strip())
            b.setObjectName(name)
            b.clicked.connect(lambda _c=False, fn=fn: fn())
            lbb.addWidget(b)
            if name == "small" and t == _(" Теки… "):
                lbb.addStretch()
        self.lib_count = QLabel()
        self.lib_count.setObjectName("dim")
        lbb.insertWidget(2, self.lib_count)
        lbv.addLayout(lbb)
        self.stack.addWidget(lb)
        ll.addWidget(self.stack, 1)
        outer.addWidget(self.lists, 1)

    def build_actions(self):
        """Меню (на macOS — у рядку меню вгорі екрана, деінде — кнопка ☰) і клавіші."""
        def act(text, fn, keys=None, checkable=False):
            a = QAction(text, self)
            if keys:
                a.setShortcuts([QKeySequence(k) for k in keys])
                a.setShortcutContext(Qt.WindowShortcut)
            a.setCheckable(checkable)
            a.triggered.connect(lambda _c=False: fn())
            self.addAction(a)
            return a

        self.a_play = act(_("Грати / пауза"), lambda: self.spawn(self.toggle()), ["Space", "X"])
        a_prev = act(_("Попередній трек"), lambda: self.spawn(self.prev()), ["Z", "Ctrl+Left", "F7"])
        a_next = act(_("Наступний трек"), lambda: self.spawn(self.next()), ["B", "Ctrl+Right", "F9"])
        a_stop = act(_("Стоп"), lambda: self.spawn(self.stop()), ["V"])
        act("pause", lambda: self.spawn(self.pause()), ["C", "F8"])
        act("seek-", lambda: self.spawn(self.seek_rel(-5)), ["Left"])
        act("seek+", lambda: self.spawn(self.seek_rel(5)), ["Right"])
        act("vol+", lambda: self.spawn(self.set_volume(self.volume + 5)), ["+", "=", "Ctrl+Up"])
        act("vol-", lambda: self.spawn(self.set_volume(self.volume - 5)), ["-", "Ctrl+Down"])
        self.a_shuffle = act(_("Перемішувати"), self.toggle_shuffle, ["S"], True)
        a_repeat = act(_("Повтор: вимк → усе → один"), self.cycle_repeat, ["R"])
        a_add = act(_("Додати теку до медіатеки…"), self.add_library_folder, ["L", "Ctrl+O"])
        a_folders = act(_("Теки медіатеки…"), self.manage_folders)
        a_find = act(_("Знайти"), self.focus_search, ["J", "/", "Ctrl+F"])
        act("tab", lambda: self.set_tab("library" if self.tab == "playlist" else "playlist"), ["Tab"])
        act("1", lambda: self.set_tab("playlist"), ["1"])
        act("2", lambda: self.set_tab("library"), ["2"])
        self.a_view = act(_("Компактний вигляд"), self.toggle_view, ["W"], True)
        self.a_mini = act(_("Міні-плеєр"), self.toggle_collapsed, ["E"], True)
        self.a_top = act(_("Поверх усіх вікон"), self.toggle_on_top, ["Ctrl+T"], True)
        self.a_popups = act(_("Сповіщення про трек"), self.toggle_popups, ["N"], True)
        a_theme = act(_("Тема: авто → світла → темна"), self.cycle_theme, ["T"])
        act("skin", self.cycle_skin, ["Shift+T"])
        self.a_tray = act(_("Згортати в трей"), self.toggle_minimize_to_tray, None, True)
        a_gh = act(_("Платівка на GitHub"), lambda: self.open_url(GITHUB_URL))
        a_bug = act(_("Повідомити про помилку"), lambda: self.open_url(ISSUES_URL))
        a_about = act(_("Про Платівку"), self.about, ["F1"])
        a_quit = act(_("Вийти з Платівки"), self.quit_app, ["Ctrl+Q", "Q"])
        a_quit.setMenuRole(QAction.QuitRole)
        a_about.setMenuRole(QAction.AboutRole)
        a_lang = act(_("Мова: українська ⇄ English"), self.toggle_language)
        act("del", self.remove_selected, ["Delete"])
        act("esc", self.escape, ["Escape"])

        def group(title, choices, fn):
            m = QMenu(title, self)
            g = QActionGroup(m)
            out = {}
            for key, text in choices:
                a = m.addAction(text)
                a.setCheckable(True)
                g.addAction(a)
                a.triggered.connect(lambda _c=False, k=key: fn(k))
                out[key] = a
            return m, out

        m_sleep, self.a_sleep = group(_("Таймер сну"), [(None, _("Вимкнено"))]
                                      + [(n, _("Через {n} хв").format(n=n)) for n in SLEEP_CHOICES]
                                      + [("track", _("Після цього треку"))], self.choose_sleep)
        m_skin, self.a_skin = group(_("Скін"), list(self.skin_names().items()), self.set_skin)
        m_rg, self.a_rg = group(_("Вирівнювання гучності (ReplayGain)"),
                                [("off", _("Вимкнено")), ("track", _("За треком")), ("album", _("За альбомом"))],
                                self.choose_replaygain)
        self.a_autoupd = act(_("Перевіряти оновлення автоматично"), self.toggle_check_updates, None, True)
        self.a_online = act(_("Шукати обкладинки в інтернеті"), self.toggle_online_covers, None, True)
        self.a_online.setToolTip(_("Якщо обкладинки немає ні у файлі, ні в теці. Надсилається лише виконавець і назва альбому."))
        a_findcover = act(_("Знайти обкладинку…"), lambda: self.pick_cover())
        a_upd = act(_("Перевірити оновлення…"), lambda: self.spawn(self.look_for_update(manual=True)))
        a_remote = act(_("Пульт з телефона…"), self.open_remote)
        a_like = act(_("До улюблених / прибрати"), lambda: self.like(), ["F"])
        a_favplay = act(_("Грати лише улюблені"), self.play_favorites, ["Shift+F"])
        a_favm3u = act(_("Зберегти улюблені як M3U…"), self.export_favorites)
        a_copy = act(_("Копіювати список на флешку…"), self.copy_playlist)
        a_dupes = act(_("Знайти дублікати…"), self.find_duplicates)
        a_unliked = act(_("Прибрати неулюблені…"), lambda: self.remove_unliked())
        a_qnext = act(_("Грати наступним"), lambda: self.play_next(), ["Shift+N"])
        a_qclear = act(_("Очистити чергу"), self.clear_queue)
        menus = [
            (_("Файл"), [a_add, a_folders, None, a_copy, a_dupes, None, a_quit]),
            (_("Відтворення"), [self.a_play, a_stop, a_prev, a_next, None, self.a_shuffle, a_repeat,
                                 None, a_qnext, a_qclear, None, m_sleep, m_rg, None, a_remote]),
            (_("Улюблені"), [a_like, a_favplay, None, a_unliked, None, a_favm3u]),
            (_("Вигляд"), [self.a_view, self.a_mini, self.a_top, None, m_skin, a_theme, self.a_popups, a_lang, None,
                           self.a_online, a_findcover, None, a_find]
             + ([self.a_tray] if not sysdeps.IS_MAC else [])),
            (_("Довідка"), [a_gh, a_bug, None, a_upd, self.a_autoupd, None, a_about]),
        ]
        popup = QMenu(self)
        for title, items in menus:
            m = self.menuBar().addMenu(title) if sysdeps.IS_MAC else popup.addMenu(title)
            for a in items:
                if a is None:
                    m.addSeparator()
                elif isinstance(a, QMenu):
                    m.addMenu(a)
                else:
                    m.addAction(a)
        if sysdeps.IS_MAC:
            self.menu_btn.hide()
        else:
            self.menuBar().hide()
            self.menu_btn.setMenu(popup)

    # ───────────── тема ─────────────
    def is_dark(self) -> bool:
        if self.base in ("light", "dark"):
            return self.base == "dark"
        try:
            return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            return False

    def apply_theme(self):
        dark = self.is_dark()
        acc = tune(self.accent_rgb, dark)
        sec = tune(self.accent_rgb, dark, .09)
        self.clock.color = QColor(acc)
        self.vu.dark = self.mini_vu.dark = dark
        self.vu.color = self.mini_vu.color = QColor(acc)
        if self.mica:
            apply_mica(self, dark)
        sk = self.skin
        if skins.vibrancy_supported() and (sk == "mac" or self.vibrancy):
            self.vibrancy = skins.set_vibrancy(self, sk == "mac", dark)
        glass = self.mica or self.vibrancy
        fg = "#F2F3F5" if dark else "#1A1D24"
        sub = "rgba(255,255,255,0.58)" if dark else "rgba(0,0,0,0.52)"
        a = QColor(acc)

        def blend(base: str, k: float) -> str:
            b = QColor(base)
            return QColor(round(b.red() + (a.red() - b.red()) * k), round(b.green() + (a.green() - b.green()) * k),
                          round(b.blue() + (a.blue() - b.blue()) * k)).name()

        def tint(base: str, k: float, alpha: float) -> str:
            c = QColor(blend(base, k))
            return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"
        # усе вікно, а не лише табло, підфарбоване кольором обкладинки
        # колір обкладинки помітний у кожному скіні: ним підфарбоване все вікно й картки
        # Вікно — тонований фон, картки — помітно світліші (у темній темі — світліші за фон):
        # інакше картки, кнопки й список зливаються в одну пляму.
        if self.vibrancy:          # macOS: під цим шаром — розмиті шпалери, тож фон майже прозорий
            bg = tint("#1E1E20" if dark else "#EEECE8", .22, .20 if dark else .16)
            card = tint("#2C2C30" if dark else "#FFFFFF", .07, .62 if dark else .72)
        elif glass:                # Windows 11: Mica
            bg = tint("#202020" if dark else "#F3F3F3", .25, .18 if dark else .22)
            card = tint("#2B2B2B" if dark else "#FFFFFF", .10, .38 if dark else .55)
        elif sk == "mac":
            bg = blend("#18191C" if dark else "#E7E5DF", .12 if dark else .11)
            card = blend("#2A2C31" if dark else "#FCFBF8", .07 if dark else .035)
        elif sk == "fluent":
            bg = blend("#1C1C1C" if dark else "#E8E8E5", .10 if dark else .11)
            card = blend("#2D2D2D" if dark else "#FDFDFC", .05 if dark else .035)
        else:
            bg = blend("#16181E" if dark else "#ECEFF4", .10 if dark else .08)
            card = blend("#1E2129" if dark else "#F7F8FB", .06 if dark else .045)
        stroke = "rgba(255,255,255,0.09)" if dark else "rgba(0,0,0,0.08)"
        lcd = QColor(acc)
        lcd.setAlpha(22 if dark else 18)
        lcd_bg = f"rgba({lcd.red()},{lcd.green()},{lcd.blue()},{lcd.alpha() / 255:.2f})"
        hl = QColor(acc)
        hl.setAlpha(50)
        hl_bg = f"rgba({hl.red()},{hl.green()},{hl.blue()},{hl.alpha() / 255:.2f})"
        groove = "rgba(255,255,255,0.16)" if dark else "rgba(0,0,0,0.14)"
        btn = "rgba(255,255,255,0.07)" if dark else "rgba(0,0,0,0.055)"
        btn_h = "rgba(255,255,255,0.14)" if dark else "rgba(0,0,0,0.10)"
        listcard = card
        for w in (self.table, self.tree):
            pal = w.palette()
            sel = QColor(acc)
            sel.setAlpha(56 if dark else 34)
            pal.setColor(pal.ColorRole.Highlight, sel)
            pal.setColor(pal.ColorRole.HighlightedText, QColor(fg))
            pal.setColor(pal.ColorRole.AlternateBase, QColor(0, 0, 0, 0))
            pal.setColor(pal.ColorRole.Base, QColor(0, 0, 0, 0))
            w.setPalette(pal)
        self._fg = fg
        # меню, діалоги й підказки — окремі вікна: даємо їм кольори теми, а не системні
        # (інакше в темній темі світлий текст опинявся на світлому меню)
        menu_bg = "#2B2D33" if dark else "#FBFBFC"
        pal = QPalette()
        for role, col in ((QPalette.Window, menu_bg), (QPalette.WindowText, fg), (QPalette.Base, "#1E2026" if dark else "#FFFFFF"),
                          (QPalette.AlternateBase, menu_bg), (QPalette.Text, fg), (QPalette.Button, menu_bg),
                          (QPalette.ButtonText, fg), (QPalette.ToolTipBase, menu_bg), (QPalette.ToolTipText, fg),
                          (QPalette.Highlight, acc), (QPalette.HighlightedText, "#FFFFFF"),
                          (QPalette.PlaceholderText, "#8A8F98")):
            pal.setColor(role, QColor(col))
        QApplication.setPalette(pal)
        self.setStyleSheet(f"""
            QMainWindow, #root {{ background: {bg}; }}
            QWidget {{ color: {fg}; }}
            #card {{ background: {card}; border: 1px solid {stroke}; border-radius: 8px; }}
            #listcard {{ background: {listcard}; border: 1px solid {stroke}; border-radius: 8px; }}
            #lcd {{ background: {lcd_bg}; border-radius: 7px; }}
            #lcd[flat="true"] {{ background: transparent; }}
            #state {{ color: {acc}; font-size: 12px; }}
            #title {{ font-size: 12px; font-weight: 600; }}
            #bigtitle {{ font-size: 13px; font-weight: 600; }}
            #sub {{ color: {acc}; font-size: 12px; }}
            #dim {{ color: {sub}; font-size: 11px; }}
            #empty {{ color: {sub}; font-size: 12px; padding: 16px; }}
            #flag {{ color: {sub}; font-size: 11px; }}
            #flagon {{ color: {acc}; font-size: 11px; font-weight: 600; }}
            QToolButton#tbtn {{ background: {btn}; border: none; border-radius: 5px; padding: 0; }}
            QToolButton#tbtn:hover {{ background: {btn_h}; }}
            QToolButton#tbtn:checked {{ background: {hl_bg}; }}
            QToolButton#tbtn::menu-indicator {{ image: none; }}
            QPushButton#small, QPushButton#primary {{ background: {btn}; border: none; border-radius: 5px;
                               padding: 3px 9px; font-size: 11px; }}
            QPushButton#small:hover {{ background: {btn_h}; }}
            QPushButton#primary {{ background: {acc}; color: {'#101215' if dark else 'white'}; font-weight: 600; }}
            QPushButton#tab, QPushButton#mode {{ background: transparent; border: none; border-radius: 6px;
                               padding: 2px 8px; color: {sub}; font-size: 12px; }}
            QPushButton#tab:hover, QPushButton#mode:hover {{ background: {btn}; }}
            QPushButton#tab[on="true"], QPushButton#mode[on="true"] {{ background: {hl_bg}; color: {acc};
                               font-weight: 600; }}
            QLineEdit {{ background: {btn}; border: 1px solid {stroke}; border-radius: 5px; padding: 2px 6px;
                         font-size: 11px; selection-background-color: {acc}; }}
            QLineEdit:focus {{ border: 1px solid {acc}; }}
            QSlider::groove:horizontal {{ height: 4px; border-radius: 2px; background: {groove}; }}
            QSlider::sub-page:horizontal {{ height: 4px; border-radius: 2px; background: {acc}; }}
            QSlider::handle:horizontal {{ width: 10px; height: 10px; margin: -4px 0; border-radius: 5px;
                               background: {'#3A3D45' if dark else 'white'}; border: 2px solid {acc}; }}
            QTableWidget, QTreeWidget {{ background: transparent; border: none; font-size: 12px; outline: 0;
                               alternate-background-color: transparent; }}
            QTableWidget::item, QTreeWidget::item {{ padding: 0 3px; border: none; }}
            QTableWidget::item:selected, QTreeWidget::item:selected {{ background: {hl_bg}; color: {fg}; }}
            QTreeWidget::item:hover, QTableWidget::item:hover {{ background: {btn}; }}
            QScrollBar:vertical {{ width: 8px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {groove}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
            QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
            QMenu {{ background: {menu_bg}; color: {fg}; border: 1px solid {stroke}; padding: 4px; }}
            QMenu::item {{ padding: 4px 22px 4px 24px; border-radius: 4px; background: transparent; }}
            QMenu::item:selected {{ background: {hl_bg}; color: {fg}; }}
            QMenu::item:disabled {{ color: {sub}; }}
            QMenu::separator {{ height: 1px; background: {stroke}; margin: 4px 8px; }}
            QDialog, QMessageBox {{ background: {menu_bg}; }}
            QListWidget {{ background: {card}; border: 1px solid {stroke}; border-radius: 6px; }}
            QToolTip {{ background: {menu_bg}; color: {fg}; border: 1px solid {stroke}; }}
            QToolButton#plain {{ background: transparent; border: none; padding: 0; }}
            QToolButton#flagicon {{ background: transparent; border: none; border-radius: 5px; padding: 0; }}
            QToolButton#flagicon:hover {{ background: {btn}; }}
            #seg {{ background: transparent; }}
        """ + self._skin_qss(dark, acc, fg, sub, card, stroke, hl_bg, btn, btn_h, groove))
        a_h = QColor(acc).lighter(112) if not dark else QColor(acc).lighter(118)
        self._acc, self._sec, self._sub, self._acc_h = acc, sec, sub, a_h.name()
        self._sub_hex = "#9A9DA4" if dark else "#6E7178"
        self._on_acc = "#101215" if dark else "#FFFFFF"
        self._size_buttons()
        self._paint_icons()
        self.update_flags()
        self.set_tab(self.tab, save=False)
        self.set_lib_mode(self.lib_mode, rebuild=False)
        self.mark_current()
        if self.cover_pix is None:
            self.cover.set_cover(placeholder_cover(acc, dark))
        self.clock.update()

    def _skin_qss(self, dark, acc, fg, sub, card, stroke, hl_bg, btn, btn_h, groove) -> str:
        """Що змінює скін поверх спільного оформлення: кнопки, вкладки, пошук, повзунки."""
        a = QColor(acc)
        rgba = lambda k: f"rgba({a.red()},{a.green()},{a.blue()},{k})"
        if self.skin == "mac":
            seg_on = "#5C5F66" if dark else "#FFFFFF"
            return f"""
            #card, #listcard {{ border-radius: 12px; border: 1px solid {stroke}; }}
            QToolButton#tbtn {{ background: transparent; border-radius: 6px; }}
            QToolButton#tbtn:hover {{ background: {btn}; }}
            QToolButton#tbtn:checked {{ background: {rgba(.18)}; }}
            QToolButton#flagicon[on="true"] {{ background: {rgba(.18)}; }}
            #seg {{ background: {'rgba(255,255,255,0.08)' if dark else 'rgba(0,0,0,0.06)'}; border-radius: 7px; }}
            QPushButton#tab {{ border-radius: 5px; padding: 2px 10px; color: {fg}; font-weight: 400; }}
            QPushButton#tab:hover {{ background: transparent; }}
            QPushButton#tab[on="true"] {{ background: {seg_on}; color: {fg}; font-weight: 500;
                               border: 1px solid {'rgba(255,255,255,0.06)' if dark else 'rgba(0,0,0,0.08)'}; }}
            QLineEdit {{ border-radius: 6px; padding: 3px 8px; font-size: 12px;
                         background: {'rgba(255,255,255,0.07)' if dark else 'rgba(0,0,0,0.05)'}; }}
            QSlider::groove:horizontal {{ background: {'rgba(255,255,255,0.14)' if dark else 'rgba(0,0,0,0.10)'}; }}
            QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
                               background: {'#C9CBD0' if dark else 'white'};
                               border: 1px solid {'rgba(0,0,0,0.35)' if dark else 'rgba(0,0,0,0.18)'}; }}
            QPushButton#small {{ background: {'rgba(255,255,255,0.10)' if dark else 'rgba(255,255,255,0.75)'};
                               border: 1px solid {'rgba(255,255,255,0.10)' if dark else 'rgba(0,0,0,0.14)'};
                               border-radius: 5px; padding: 2px 9px; font-size: 11px; }}
            QPushButton#primary {{ border-radius: 5px; }}
            QMenu {{ border-radius: 8px; }}
            """
        if self.skin == "fluent":
            ctl = "rgba(255,255,255,0.06)" if dark else "rgba(255,255,255,0.72)"
            ctl_b = "rgba(255,255,255,0.09)" if dark else "rgba(0,0,0,0.08)"
            ctl_bb = "rgba(255,255,255,0.05)" if dark else "rgba(0,0,0,0.18)"
            return f"""
            #card, #listcard {{ border-radius: 8px; border: 1px solid {stroke}; }}
            QToolButton#tbtn {{ background: transparent; border-radius: 4px; }}
            QToolButton#tbtn:hover {{ background: {btn}; }}
            QToolButton#tbtn:checked {{ background: {rgba(.22)}; }}
            QToolButton#flagicon {{ background: {ctl}; border: 1px solid {ctl_b}; border-bottom-color: {ctl_bb};
                               border-radius: 4px; }}
            QToolButton#flagicon:hover {{ background: {btn_h}; }}
            QToolButton#flagicon[on="true"] {{ background: {acc}; border: 1px solid {acc}; }}
            QPushButton#tab {{ border-radius: 0; padding: 4px 8px 2px; color: {sub}; font-size: 13px;
                               border-bottom: 3px solid transparent; background: transparent; }}
            QPushButton#tab:hover {{ background: transparent; color: {fg}; }}
            QPushButton#tab[on="true"] {{ background: transparent; color: {fg}; font-weight: 600;
                               border-bottom: 3px solid {acc}; }}
            QLineEdit {{ border-radius: 4px; padding: 4px 8px; font-size: 12px; background: {ctl};
                         border: 1px solid {ctl_b}; border-bottom: 1px solid {'rgba(255,255,255,0.5)' if dark else 'rgba(0,0,0,0.45)'}; }}
            QLineEdit:focus {{ border-bottom: 2px solid {acc}; }}
            QSlider::groove:horizontal {{ background: {'rgba(255,255,255,0.5)' if dark else 'rgba(0,0,0,0.42)'}; }}
            QSlider::handle:horizontal {{ width: 18px; height: 18px; margin: -7px 0; border-radius: 9px;
                               border: 1px solid {'rgba(0,0,0,0.3)' if dark else 'rgba(0,0,0,0.12)'};
                               background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                   stop:0 {acc}, stop:0.52 {acc}, stop:0.6 {'#454545' if dark else 'white'},
                                   stop:1 {'#454545' if dark else 'white'}); }}
            QPushButton#small {{ background: {ctl}; border: 1px solid {ctl_b}; border-bottom-color: {ctl_bb};
                               border-radius: 4px; padding: 3px 10px; font-size: 12px; }}
            QPushButton#primary {{ border-radius: 4px; padding: 3px 10px; font-size: 12px; }}
            QMenu {{ border-radius: 8px; }}
            QMenu::item {{ border-radius: 4px; }}
            QTableWidget::item {{ padding: 0 3px 0 9px; }}
            """
        return ""

    def _icon(self, kind: str, color: str):
        fam = self.skin if self.skin != "classic" else None
        if fam:
            ic = skins.line_icon(kind, color, fam)
            if ic is not None:
                return ic
        if kind in ("shuffle", "repeat", "repeat1", "bell", "bell_off", "phone", "speaker", "mute"):
            return skins.line_icon(kind, color, "mac") or QIcon()
        return glyph_icon(kind, color)

    def _paint_icons(self):
        fg = getattr(self, "_fg", "#1A1D24")
        for b in list(self.buttons.values()) + [self.pin, self.collapse_btn, self.menu_btn]:
            g = b.property("glyph")
            if g:
                b.setIcon(self._icon(g, fg))
        self._paint_toggle()
        sub = getattr(self, "_sub_hex", "#6E7178")
        self.vol_icon.setIcon(self._icon("mute" if self.sys_muted or self.volume == 0 else "speaker",
                                         fg if self.skin == "fluent" else sub))

    def _paint_toggle(self):
        if not hasattr(self, "_fg"):
            return
        playing = getattr(self, "_playing", False)
        col = self._on_acc if self.skin == "fluent" else self._fg
        b = self.buttons["toggle"]
        b.setIcon(self._icon("pause" if playing else "play", col))
        b.setToolTip(_("Пауза") if playing else _("Грати"))

    def cycle_theme(self):
        self.base = {"auto": "light", "light": "dark", "dark": "auto"}.get(self.base, "auto")
        self.apply_theme()
        self.toast({"auto": _("Тема: як у системі"), "light": _("Тема: світла"), "dark": _("Тема: темна")}[self.base])
        self.save_cfg()

    def showEvent(self, e):
        super().showEvent(e)
        if self.skin == "mac" and skins.vibrancy_supported() and not self.vibrancy:
            QTimer.singleShot(0, self.apply_theme)      # NSWindow з'являється лише після показу
        if self._want_mica and not self.mica:
            self.mica = apply_mica(self, self.is_dark())
            log(f"mica: {self.mica}")
            if self.mica:
                self.apply_theme()
            else:
                self.setAttribute(Qt.WA_TranslucentBackground, False)
                self.apply_theme()

    def changeEvent(self, e):
        if e.type() == QEvent.ThemeChange and self.base == "auto":
            QTimer.singleShot(0, self.apply_theme)
        if e.type() == QEvent.WindowStateChange and self.isMinimized() and self.minimize_to_tray and self.tray:
            QTimer.singleShot(0, self.hide)
        super().changeEvent(e)

    # ───────────── вигляд ─────────────
    def is_full(self) -> bool:
        return self.view == "full" and not self.collapsed

    def apply_view(self, initial=False, expand=False):
        """Повний вигляд, компактний (два ряди над списком) чи міні-плеєр (лише ці два ряди).

        expand — вікно щойно розгорнули з міні-плеєра: повертаємо йому колишню висоту.
        """
        full = self.is_full()
        self.cover.set_size(128 if full else 44)
        for w in (self.clock, self.vu, self.state, self.title, self.info):
            w.setVisible(full)
        for w in (self.c_title, self.c_sub):
            w.setVisible(not full)
        self.lists.setVisible(not self.collapsed)
        self.collapse_btn.setProperty("glyph", "down" if self.collapsed else "up")
        self.collapse_btn.setToolTip(_("Розгорнути") if self.collapsed else _("Міні-плеєр"))
        self.a_view.setChecked(self.view == "compact")
        self.a_mini.setChecked(self.collapsed)
        self.tab_pl.setText(_("Список відтворення") if full else _("Список"))
        self._layout_card(full)
        self._lcd_gap.changeSize(0, 6 if full else 0)
        self.lcd.layout().setContentsMargins(*(10, 6, 10, 6) if full else (0, 0, 0, 0))
        self.lcd.layout().setSpacing(2 if full else 0)
        self.lcd.layout().invalidate()
        self.lcd.setProperty("flat", not full)
        self.lcd.style().unpolish(self.lcd)
        self.lcd.style().polish(self.lcd)
        self.card.layout().setSpacing(6 if full else 5)
        self.card.layout().setContentsMargins(*(10, 10, 10, 8) if full else (8, 6, 8, 6))
        self._outer.setContentsMargins(*(8, 8, 8, 8) if full else (6, 6, 6, 6))
        self.top_row.setSpacing(10 if full else 8)
        self._size_buttons()
        self._paint_icons()
        self.update_flags()
        if self.collapsed:
            self.setMinimumHeight(0)
            QTimer.singleShot(0, self._fit_mini)
        elif expand and not initial:
            self.setMaximumHeight(16777215)
            self.resize(self.width(), max(self._expanded_h, 420))
        else:
            self.setMaximumHeight(16777215)
        self.update_now_playing()

    def _layout_card(self, full: bool):
        """Розкласти кнопки, смугу й гучність по рядах картки — для повного чи компактного вигляду."""
        for lay in (self.tr, self.sr, self.tcl):
            while lay.count():
                lay.takeAt(0)          # віджети лишаються в картці, порожні проміжки — зникають
        lv = self.lcd.layout()
        lv.removeWidget(self.flagw)
        b = self.buttons
        sys_skin = self.skin != "classic"
        shown = set()

        def add(lay, *ws, stretch=0):
            for w in ws:
                lay.addWidget(w, stretch)
                shown.add(w)
        if full:
            add(self.tr, b["prev"], *((b["toggle"],) if sys_skin else (b["play"], b["pause"])), b["stop"], b["next"],
                b["eject"])
            self.tr.addStretch()
            add(self.tr, self.collapse_btn)
            self.tr.addSpacing(6)
            add(self.tr, self.vol_icon if sys_skin else self.vol_label)
            add(self.tr, self.vol, self.vol_pct)
            add(self.sr, self.seek, stretch=1)
            add(self.sr, self.time)
            lv.addWidget(self.flagw)
        else:
            # два ряди: [обкладинка · назва · ⏮ ⏯ ⏭ · шпилька · згорнути] і [перемикачі · час ━━ час · гучність]
            add(self.tcl, b["prev"], b["toggle"], b["next"])
            self.tcl.addSpacing(2)
            add(self.tcl, self.pin, self.collapse_btn)
            add(self.sr, self.flagw)
            self.sr.addSpacing(2)
            add(self.sr, self.pos_lbl)
            add(self.sr, self.seek, stretch=1)
            add(self.sr, self.time)
            self.sr.addSpacing(4)
            add(self.sr, self.vol_icon, self.vol)
        for w in self._card_widgets:
            w.setVisible(w in shown)
        self.flagw.show()

    def _size_buttons(self):
        """Розміри кнопок залежать від скіна: у Windows вони більші (так велить Fluent), у macOS — без рамок."""
        full = self.is_full()
        sk = self.skin
        if sk == "mac":
            tb, ic, sm, fl, rail = ((34, 28), 15, (26, 26), (28, 24), 20) if full else ((28, 26), 14, (24, 26), (22, 20), 20)
            tog = (40, 30) if full else (30, 26)
        elif sk == "fluent":
            tb, ic, sm, fl, rail = ((36, 36), 16, (32, 32), (32, 28), 22) if full else ((30, 32), 14, (28, 30), (24, 22), 22)
            tog = (44, 44) if full else (34, 34)
        else:
            tb, ic, sm, fl, rail = ((30, 22), 12, (26, 22), (20, 20), 16) if full else ((28, 24), 12, (22, 24), (20, 20), 16)
            tog = tb if full else (32, 24)
        for k, btn in self.buttons.items():
            btn.setFixedSize(*(tog if k == "toggle" else tb))
            isz = ic + (2 if k == "toggle" and sk != "classic" else 0)
            btn.setIconSize(QSize(isz, isz))
        for btn in (self.pin, self.collapse_btn):
            btn.setFixedSize(*sm)
            btn.setIconSize(QSize(12 if sk == "classic" else 14, 12 if sk == "classic" else 14))
        for btn in self.icon_flags.values():
            btn.setFixedSize(*fl)
            btn.setIconSize(QSize(14, 14))
        self.vol_icon.setFixedSize(20, 20)
        for sl in (self.seek, self.vol):
            sl.setFixedHeight(rail)
        self.vol.setFixedWidth(90 if full else 56)
        tbl = getattr(self, "table", None)
        if tbl is not None:
            tbl.verticalHeader().setDefaultSectionSize({"mac": 26, "fluent": 30}.get(sk, 22))
        # Windows 11: «грати/пауза» — кругла кнопка кольору обкладинки
        t = self.buttons["toggle"]
        if sk == "fluent" and hasattr(self, "_acc"):
            r = tog[0] // 2
            t.setStyleSheet(f"QToolButton {{ background: {self._acc}; border: none; border-radius: {r}px; }}"
                            f"QToolButton:hover {{ background: {self._acc_h}; }}")
        else:
            t.setStyleSheet("")

    def _fit_mini(self):
        self.layout().activate()
        h = self.card.sizeHint().height() + 20
        self.setMaximumHeight(h)
        self.resize(self.width(), h)

    def toggle_view(self):
        self.view = "compact" if self.view == "full" else "full"
        was = self.collapsed
        if self.collapsed:
            self.collapsed = False
        self.apply_view(expand=was)
        self.save_cfg()

    def set_skin(self, skin: str, toast=True):
        if skin not in skins.SKINS:
            return
        self.skin = skin
        self.apply_theme()
        self.apply_view()
        if toast:
            self.toast(_("Скін: {name}").format(name=self.skin_names()[skin]))
        self.save_cfg()

    def cycle_skin(self):
        i = skins.SKINS.index(self.skin)
        self.set_skin(skins.SKINS[(i + 1) % len(skins.SKINS)])

    @staticmethod
    def skin_names() -> dict:
        return {"classic": _("Платівка (класичний)"), "mac": "macOS", "fluent": "Windows 11"}

    def toggle_collapsed(self):
        if not self.collapsed:
            self._expanded_h = self.height()
        self.collapsed = not self.collapsed
        self.apply_view(expand=not self.collapsed)
        self.save_cfg()

    def toggle_on_top(self):
        self.on_top = not self.on_top
        self.pin.setChecked(self.on_top)
        self.a_top.setChecked(self.on_top)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.on_top)
        self.show()
        self.save_cfg()

    def set_tab(self, tab: str, save=True):
        self.tab = tab if tab in ("playlist", "library") else "playlist"
        self.stack.setCurrentIndex(0 if self.tab == "playlist" else 1)
        for b, t in ((self.tab_pl, "playlist"), (self.tab_lib, "library")):
            b.setProperty("on", t == self.tab)
            b.style().unpolish(b)
            b.style().polish(b)
        if self.collapsed and save:
            self.toggle_collapsed()
        self.apply_filter(self.search.text())
        (self.table if self.tab == "playlist" else self.tree).setFocus()
        if save:
            self.save_cfg()

    def focus_search(self):
        if self.collapsed:
            self.toggle_collapsed()
        self.search.setFocus()
        self.search.selectAll()

    def escape(self):
        if self.search.hasFocus() or self.search.text():
            self.search.clear()
            (self.table if self.tab == "playlist" else self.tree).setFocus()

    # ───────────── доступ до треків ─────────────
    def track(self, path: str) -> Track:
        t = self.lib.tracks.get(path) or self.extra.get(path)
        if t is None:
            t = self.extra[path] = read_track(path)
        return t

    def spawn(self, coro):
        try:
            return asyncio.ensure_future(coro)
        except RuntimeError:   # цикл подій уже закрито (вихід)
            coro.close()
            return None

    # сумісність із модулями mpris / smtc (вони писались для консольної версії)
    def run_worker(self, coro):
        return self.spawn(coro)

    def call_from_thread(self, fn, *args):
        self.bridge.call.emit(lambda: fn(*args))

    def toggle_from_tray(self):
        self.spawn(self.toggle())

    def next_from_tray(self):
        self.spawn(self.next())

    def prev_from_tray(self):
        self.spawn(self.prev())

    async def action_quit(self):
        self.quit_app()

    # ───────────── відтворення ─────────────
    async def start_player(self):
        cls = DemoPlayer if self.demo else MpvPlayer
        self.player = cls(self._mpv_eof, self._mpv_error, self._mpv_message, self._mpv_external_pause)
        self.player.replaygain, self.player.on_advance = self.replaygain, self._mpv_advance
        try:
            await self.player.start(self.player_volume)
        except FileNotFoundError:
            QMessageBox.critical(self, APP_NAME, _("Для звуку потрібен mpv.") + "\n\n" +
                                 (sysdeps.mpv_install_hint() or ""))
            self.player = DemoPlayer(self._mpv_eof, self._mpv_error, self._mpv_message)
            await self.player.start(self.player_volume)
        if self.volume_mode == "system" and not self.demo:
            self._init_sysvol()
        if 0 <= self.current < len(self.playlist) and os.path.exists(real_path(self.playlist[self.current])):
            await self.play_index(self.current, start=float(self.cfg.get("position", 0)), paused=True)
        else:
            self.current = -1
        self.setup_platform()

    async def play_index(self, i: int, start: float = 0.0, paused: bool = False):
        if not (0 <= i < len(self.playlist)) or self.player is None:
            return
        self._load_gen += 1
        gen = self._load_gen
        async with self._load_lock:
            if gen != self._load_gen:
                return
            if self.current != i and self.current >= 0:
                self.history = (self.history + [self.current])[-200:]
            self.current = i
            self.stopped = False
            path = self.playlist[i]
            await self.load_track(path, start=start, paused=paused)
            if not paused:
                self.announce(path)
            self.update_now_playing()
            self.mark_current()
            self.load_cover(path)
            self.save_cfg()

    async def play(self):
        if not self.playlist:
            self.toast(_("Список порожній — оберіть музику в медіатеці"))
            return
        if self.player.active and self.player.paused:
            await self.player.set_pause(False)
        elif self.player.active:
            await self.player.seek(0)
        else:
            i = self.current if self.current >= 0 else max(0, self.table.currentRow())
            await self.play_index(i)

    async def pause(self):
        if self.player and self.player.active:
            await self.player.set_pause(not self.player.paused)

    async def toggle(self):
        if self.player and self.player.active:
            await self.player.set_pause(not self.player.paused)
        else:
            await self.play()

    async def stop(self):
        if self.player:
            await self.player.stop()
        self.stopped = True

    def next_index(self, auto: bool):
        n = len(self.playlist)
        if not n:
            return None
        if auto and self.repeat == "one":
            return self.current
        q = self.queue_index()
        if q is not None:
            return q
        if self.shuffle and n > 1:
            recent = set(self.history[-max(1, n // 2):] + [self.current])
            pool = [i for i in range(n) if i not in recent] or [i for i in range(n) if i != self.current]
            return random.choice(pool)
        j = self.current + 1
        if j >= n:
            return 0 if (self.repeat == "all" or not auto) else None
        return j

    async def next(self, auto: bool = False):
        j = self.next_index(auto)
        if j is None:
            self.stopped = True
            await self.player.stop()
            if auto and self.playlist:
                self.toast(_("Список відтворення закінчився. Повтор усього: клавіша R"))
            return
        await self.play_index(j)

    async def prev(self):
        if self.player.active and self.player.time_pos > 3:
            await self.player.seek(0)
            return
        if self.shuffle and self.history:
            j = self.history.pop()
            if 0 <= j < len(self.playlist):
                self.current = -1
                await self.play_index(j)
                return
        if self.playlist:
            await self.play_index((self.current - 1) % len(self.playlist))

    async def seek_rel(self, d: float):
        if self.player and self.player.active:
            await self.player.seek(self.player.time_pos + d)

    async def seek_frac(self, f: float):
        if self.player and self.player.active and self.player.duration:
            await self.player.seek(f * self.player.duration)

    def _mpv_eof(self, early=None):
        if early:
            pos, dur = early
            self.toast(_("Трек обірвався на {pos} з {dur}: файл, схоже, обрізаний або пошкоджений. "
                         "Вмикаю наступний.").format(pos=fmt_time(pos), dur=fmt_time(dur)))
        if self.sleep_consume_eof():
            self.spawn(self.stop())
            self.update_flags()
            self.toast(_("Таймер сну: трек закінчився, музику зупинено"))
            return
        self.spawn(self.next(auto=True))

    def _mpv_advance(self, path: str):
        """Gapless: mpv сам перейшов до наступного файлу — показуємо його поточним."""
        self.spawn(self._advanced(path))

    async def _advanced(self, path: str):
        j = self.gapless_index(path)
        if j is None:
            return
        self.mark_advanced(j)
        self.stopped = False
        self.announce(self.playlist[j])
        self.update_now_playing()
        self.mark_current()
        self.load_cover(self.playlist[j])
        self.save_cfg()
        await self.refresh_preload()

    def _mpv_error(self, err):
        name = Path(self.playlist[self.current]).name if 0 <= self.current < len(self.playlist) else ""
        self.toast(_("Не вдалося відтворити {name}").format(name=name))
        self.spawn(self.next(auto=True))

    def _mpv_message(self, args):
        if not args:
            return
        log(f"медіаклавіша: {args}")
        if args[0] == "plativka-next":
            self.spawn(self.next())
        elif args[0] == "plativka-prev":
            self.spawn(self.prev())
        elif args[0] == "plativka-stop":
            self.spawn(self.stop())

    def _mpv_external_pause(self, paused: bool):
        pass

    # ───────────── гучність (дзеркало системної) ─────────────
    async def set_volume(self, v: int):
        self.volume = int(clamp(v, 0, 100))
        if self.sysvol is not None:
            self.sys_muted = False
            threading.Thread(target=self._sysvol_set, args=(self.volume,), daemon=True).start()
        else:
            self.player_volume = self.volume
            if self.player:
                await self.player.set_volume(self.volume)
        self._refresh_volume()

    def _vol_icon_clicked(self):
        """Іконка гучності: вимкнути звук, а якщо він вимкнений — повернути попередню гучність."""
        if self.sys_muted or self.volume == 0:
            self.spawn(self.set_volume(getattr(self, "_vol_before_mute", 0) or 40))
        else:
            self._vol_before_mute = self.volume
            self.spawn(self.set_volume(0))

    def _vol_moved(self, v: int):
        if v != self.volume and not getattr(self, "_vol_sync", False):
            self.spawn(self.set_volume(v))

    def _refresh_volume(self):
        self._vol_sync = True
        self.vol.setValue(self.volume)
        self._vol_sync = False
        self.vol_pct.setText(_("без звуку ").strip() if self.sys_muted else f"{self.volume}%")
        self.vol.setToolTip(_("Гучність") + f": {self.vol_pct.text()}")
        if hasattr(self, "_fg"):
            self.vol_icon.setIcon(self._icon("mute" if self.sys_muted or self.volume == 0 else "speaker",
                                             self._fg if self.skin == "fluent" else self._sub_hex))

    def _init_sysvol(self):
        def work():
            sysvol.init_thread()
            sv = sysvol.detect()
            if sv is None:
                log("sysvol: недоступна, лишається гучність плеєра")
                return
            self.call_from_thread(self._sysvol_ready, sv)
            while not self._quitting and self.volume_mode == "system":
                try:
                    r = sv.get()
                except Exception:
                    r = None
                if r is not None:
                    self.call_from_thread(self._sysvol_changed, *r)
                time.sleep(0.7)
        threading.Thread(target=work, daemon=True).start()

    def _sysvol_ready(self, sv):
        self.sysvol = sv
        if self.player:
            self.spawn(self.player.set_volume(100))

    def _sysvol_changed(self, v: int, muted: bool):
        if self.sysvol is None:
            return
        if (v, muted) != (self.volume, self.sys_muted) and time.monotonic() - self._sysvol_t > 0.8:
            self.volume, self.sys_muted = v, muted
            self._refresh_volume()

    def _sysvol_set(self, v: int):
        self._sysvol_t = time.monotonic()
        sysvol.init_thread()
        if self.sysvol is not None:
            self.sysvol.set(v)

    # ───────────── оновлення екрана ─────────────
    def tick(self):
        p = self.player
        if p is None:
            return
        dur = p.duration or (self.track(self.playlist[self.current]).length if 0 <= self.current < len(self.playlist) else 0)
        pos = p.time_pos if p.active else 0
        if not self.seek.dragging:
            self.seek.blockSignals(True)
            self.seek.setValue(int(1000 * pos / dur) if dur else 0)
            self.seek.blockSignals(False)
        if self.remaining and dur:
            self.clock.set_text("-" + fmt_time(max(0, dur - pos)))
        else:
            self.clock.set_text(fmt_time(pos) if p.active else "-:--")
        self.time.setText(fmt_time(dur) if dur else "-:--")
        if not self.is_full():
            self.pos_lbl.setText(fmt_time(pos) if p.active else "-:--")
        st = "▶" if p.active and not p.paused else ("❚❚" if p.active else "■")
        self.state.setText(st)
        playing = bool(p.active and not p.paused)
        if playing != getattr(self, "_playing", False):
            self._playing = playing
            self._paint_toggle()
        self.setWindowTitle(f"{self._now_title} — {APP_NAME}" if p.active and self._now_title else APP_NAME)
        if self.tray is not None:
            self.tray.setToolTip(f"{APP_NAME}\n{self._now_title}" if self._now_title else APP_NAME)
        if self.sleep_until:
            self.f_sleep.setText(self.sleep_label())
            if self.sleep_left == 0:
                self.spawn(self._sleep_fire())
        self._platform_tick()

    async def vu_tick(self):
        if self.player is None or not self.isVisible():
            return
        await self.player.poll_levels()
        p = self.player
        (self.vu if self.vu.isVisible() else self.mini_vu).show_levels(p.levels, p.peaks, p.vu_ok)

    _now_title = ""

    def update_now_playing(self):
        if 0 <= self.current < len(self.playlist):
            t = self.track(self.playlist[self.current])
            self._now_title = t.display
            heart = ' <span style="color:#e0245e">♥</span>' if self.is_fav(self.playlist[self.current]) else ""
            self.title.setText(html.escape(f"{self.current + 1}. {t.display} ({fmt_time(t.length)})") + heart)
            parts = [t.fmt]
            if t.bitrate:
                parts.append(_("{kbps} кбіт/с").format(kbps=t.bitrate // 1000))
            if t.samplerate:
                parts.append(_("{khz} кГц").format(khz=f"{t.samplerate / 1000:g}"))
            if t.channels:
                parts.append(_("стерео") if t.channels >= 2 else _("моно"))
            album = " · ".join(x for x in (t.album, t.year) if x)
            self.info.setText("  ".join(parts) + (f"    {album}" if album else ""))
            self.c_title.setText(html.escape(t.title or t.display) + heart)
            self.c_sub.setText(" — ".join(x for x in (t.artist, " · ".join(y for y in (t.album, t.year) if y)) if x))
        else:
            self._now_title = ""
            self.title.setText(html.escape(_("{app} {ver} — оберіть, що послухати").format(app=APP_NAME, ver=VERSION)))
            self.info.setText("")
            self.c_title.setText(html.escape(APP_NAME))
            self.c_sub.setText(_("оберіть, що послухати"))
        self._refresh_volume()

    def update_flags(self):
        if not hasattr(self, "_acc"):
            return
        self.f_shuffle.setText(_("перемішати"))
        self.f_shuffle.setObjectName("flagon" if self.shuffle else "flag")
        self.f_repeat.setText({"off": _("повтор: вимк"), "all": _("повтор: все"), "one": _("повтор: один")}[self.repeat])
        self.f_repeat.setObjectName("flagon" if self.repeat != "off" else "flag")
        self.f_popups.setText(_("сповіщ: {os}").format(os=sysdeps.OS_NAME) if self.popups else _("сповіщ: вимк"))
        self.f_popups.setObjectName("flagon" if self.popups else "flag")
        for w in (self.f_shuffle, self.f_repeat, self.f_popups):
            w.style().unpolish(w)
            w.style().polish(w)
        self.a_shuffle.setChecked(self.shuffle)
        self.a_popups.setChecked(self.popups)
        self.a_tray.setChecked(self.minimize_to_tray)
        sl = self.sleep_label()
        self.f_sleep.setText(sl)
        self.f_sleep.setToolTip(_("Клацніть, щоб вимкнути таймер сну"))
        self.f_sleep.setVisible(bool(sl))
        cur = "track" if self.sleep_after_track else (self.sleep_minutes if self.sleep_until else None)
        for key, a in self.a_sleep.items():
            a.setChecked(key == cur)
        for key, a in self.a_rg.items():
            a.setChecked(key == self.replaygain)
        self.a_autoupd.setChecked(self.check_updates)
        self.a_online.setChecked(self.online_covers)
        on = bool(self.remote and self.remote.running)
        self.f_remote.setText(_("пульт"))
        self.f_remote.setToolTip(_("Пульт з телефона увімкнено — клацніть, щоб відкрити"))
        # перемикачі словами (класичний повний вигляд) чи іконками (скіни macOS/Windows і компактний вигляд)
        icons = self.skin != "classic" or not self.is_full()
        for w in (self.f_shuffle, self.f_repeat, self.f_popups):
            w.setVisible(not icons)
        self.f_remote.setVisible(on and not icons)
        self._flags_l.setSpacing(4 if icons else 14)
        on_col = self._on_acc if self.skin == "fluent" else self._acc
        rep_txt = {"off": _("повтор: вимк"), "all": _("повтор: все"), "one": _("повтор: один")}[self.repeat]
        for key, state, kind, tip in (
                ("shuffle", self.shuffle, "shuffle", _("Перемішувати") + (" ✓" if self.shuffle else "")),
                ("repeat", self.repeat != "off", "repeat1" if self.repeat == "one" else "repeat", rep_txt),
                ("popups", self.popups, "bell" if self.popups else "bell_off",
                 _("сповіщ: {os}").format(os=sysdeps.OS_NAME) if self.popups else _("сповіщ: вимк")),
                ("remote", True, "phone", _("Пульт з телефона увімкнено — клацніть, щоб відкрити"))):
            b = self.icon_flags[key]
            b.setVisible(icons and (on if key == "remote" else True))
            b.setProperty("on", bool(state))
            b.setIcon(self._icon(kind, on_col if state else self._sub_hex))
            b.setToolTip(tip)
            b.style().unpolish(b)
            b.style().polish(b)
        for key, a in getattr(self, "a_skin", {}).items():
            a.setChecked(key == self.skin)
        u = self.update_info
        self.f_update.setVisible(bool(u))
        if u:
            self.f_update.setText("⬆ " + u["version"])
            self.f_update.setToolTip(_("Вийшла нова версія — клацніть, щоб завантажити"))

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.update_flags()
        self.save_cfg()
        self.spawn(self.refresh_preload())

    # ── таймер сну, вирівнювання гучності, оновлення ──
    def choose_sleep(self, minutes):
        self.set_sleep(minutes)
        self.update_flags()
        self.spawn(self.refresh_preload())
        if minutes is None:
            self.toast(_("Таймер сну вимкнено"))
        elif minutes == "track":
            self.toast(_("Таймер сну: зупиню після цього треку"))
        else:
            self.toast(_("Таймер сну: зупиню через {n} хв").format(n=minutes))

    async def _sleep_fire(self):
        if await self.sleep_tick():
            self.update_flags()
            self.toast(_("Таймер сну: музику поставлено на паузу"))

    def choose_replaygain(self, mode: str):
        self.replaygain = mode
        if self.player:
            self.spawn(self.player.set_replaygain(mode))
        self.update_flags()
        self.save_cfg()

    # ── обкладинки з інтернету ──
    def toggle_online_covers(self):
        self.online_covers = not self.online_covers
        self.update_flags()
        self.save_cfg()
        if self.online_covers:
            self.toast(_("Шукатиму обкладинки, яких немає у файлах: MusicBrainz, запасний — Apple. "
                         "Надсилається лише виконавець і назва альбому."))
            if 0 <= self.current < len(self.playlist) and self._cover_img is None:
                self._fetch_online_cover(self.playlist[self.current])

    def _fetch_online_cover(self, path: str):
        from . import covers
        covers.fetch_in_background(self.track(path), lambda jpg: self.call_from_thread(self._online_cover_ready, path))

    def _online_cover_ready(self, path: str):
        self.cover_rev += 1
        if 0 <= self.current < len(self.playlist) and self.playlist[self.current] == path:
            self._cover_path = None
            self.load_cover(path)

    def pick_cover(self, path: str | None = None):
        if path is None and 0 <= self.current < len(self.playlist):
            path = self.playlist[self.current]
        if not path:
            self.toast(_("Спершу увімкніть трек"))
            return
        t = self.track(path)
        if not (t.albumartist or t.artist) or not (t.album or t.title):
            self.toast(_("У треку немає виконавця й назви — нема за чим шукати"))
            return
        from .core import find_cover
        if find_cover(path):
            self.toast(_("У цього треку вже є обкладинка у файлі чи в теці — вона головніша за знайдену"))
            return
        CoverPickDialog(self, path).exec()

    def toggle_check_updates(self):
        self.check_updates = not self.check_updates
        self.update_flags()
        self.save_cfg()
        if self.check_updates:
            self.spawn(self.look_for_update())

    async def look_for_update(self, manual: bool = False):
        info = await asyncio.to_thread(check_update, manual)
        if info and info.get("error"):
            if manual:          # не кажемо «найновіша», якщо насправді не змогли спитати
                self.toast(_("Не вдалося перевірити оновлення: немає зв'язку з GitHub. Спробуйте пізніше."))
            return
        self.update_info = info
        self.update_flags()
        if info:
            self.toast(_("Вийшла Платівка {v} — натисніть «⬆ {v}», щоб завантажити").format(v=info["version"]))
        elif manual:
            self.toast(_("У вас найновіша версія ({v})").format(v=VERSION))

    # ── пульт з телефона ──
    def open_remote(self):
        RemoteDialog(self).exec()

    async def set_remote(self, on: bool):
        from .remote import RemoteServer
        if on:
            if self.remote is None:
                self.remote = RemoteServer(self, self.remote_cfg, self.save_cfg)
            try:
                await self.remote.start()
            except OSError as e:
                self.toast(_("Не вдалося увімкнути пульт: {e}").format(e=e))
                return
        elif self.remote:
            await self.remote.stop()
        self.remote_cfg["enabled"] = on
        self.update_flags()
        self.save_cfg()

    def remote_accent(self) -> str:
        return tune(self.accent_rgb, self.is_dark())

    def remote_dark(self) -> bool:
        return self.is_dark()

    def remote_like(self, path: str):
        self.like(path)

    def remote_queue(self, path: str):
        self.play_next([path])

    def remote_event(self, kind: str, text: str):
        msg = {"paired": _("Підключено пульт: {name}"), "left": _("Пульт відключився: {name}"),
               "blocked": _("Пульт: адресу {name} заблоковано після невдалих спроб підключення"),
               "code_locked": _("Пульт: забагато неправильних кодів — код вимкнено. Покажіть новий, якщо треба.")}
        text = msg.get(kind, "{name}").format(name=text)
        self.toast(text)
        if not self.isActiveWindow() and kind in ("paired", "blocked"):
            self._tray_message(APP_NAME, text)

    def open_update(self):
        if self.update_info:
            self.open_url(self.update_info["url"])

    def cycle_repeat(self):
        self.repeat = {"off": "all", "all": "one", "one": "off"}[self.repeat]
        self.spawn(self.refresh_preload())
        self.update_flags()
        self.save_cfg()

    def toggle_popups(self):
        self.popups = not self.popups
        self.update_flags()
        self.save_cfg()

    def toggle_remaining(self):
        self.remaining = not self.remaining
        self.tick()

    def toggle_minimize_to_tray(self):
        self.minimize_to_tray = not self.minimize_to_tray
        self.update_flags()
        self.save_cfg()

    def toast(self, text: str):
        """Коротке повідомлення в рядку під кнопками (не заважає роботі)."""
        log(f"toast: {text}")
        sb = self.statusBar()
        sb.show()
        sb.showMessage(text, 5000)
        QTimer.singleShot(5200, lambda: sb.hide() if not sb.currentMessage() else None)

    # ───────────── обкладинка ─────────────
    def load_cover(self, path: str):
        if path == self._cover_path:
            return
        self._cover_path = path

        def work():
            try:
                img = load_cover(path, track=self.track(path))
            except Exception:
                img = None
            self.call_from_thread(self._set_cover, path, img)
            if img is None and self.online_covers:
                self._fetch_online_cover(path)
        threading.Thread(target=work, daemon=True).start()

    def _set_cover(self, path, img):
        if path != self._cover_path:
            return
        self._cover_img = img
        if img is not None:
            self.cover_pix = pil_to_pixmap(img)
            self.accent_rgb = accent_from(img) or DEFAULT_ACCENT
        else:
            self.cover_pix = None
            self.accent_rgb = DEFAULT_ACCENT
        self._cover_file = self._write_cover_file(path, img) if (self.mpris or self.smtc) else None
        self.apply_theme()
        if self.cover_pix is not None:
            self.cover.set_cover(self.cover_pix)
        if self.tray is not None:
            self.tray.setIcon(QIcon(self.cover_pix) if self.cover_pix is not None else app_icon())

    def _write_cover_file(self, path: str, img):
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for old in CACHE_DIR.glob("cover-*.jpg"):
                old.unlink(missing_ok=True)
            if img is None:
                return None
            f = CACHE_DIR / f"cover-{abs(hash(path)) % 10 ** 8}.jpg"
            img.convert("RGB").save(f, "JPEG", quality=88)
            return f
        except Exception:
            return None

    # ───────────── сповіщення ─────────────
    def announce(self, path: str):
        if not self.popups or (self.isActiveWindow() and not self.collapsed):
            return
        t = self.track(path)
        head, body = t.artist or APP_NAME, t.title
        sub = " · ".join(x for x in (t.album, t.year) if x)
        img = self._cover_img if self._cover_path == path else None

        def work():
            im = img
            if im is None:
                try:
                    im = load_cover(path)
                except Exception:
                    im = None
            cover = None
            if im is not None:
                try:
                    small = im.convert("RGB")
                    small.thumbnail((256, 256))
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cover = CACHE_DIR / "notify-cover.jpg"
                    small.save(cover, "JPEG", quality=85)
                except Exception:
                    cover = None
            if sysdeps.IS_WIN:
                from . import winnotify
                if winnotify.show(head, body + (f"\n{sub}" if sub else ""), str(cover) if cover else None):
                    return
                self.call_from_thread(self._tray_message, head, body + (f"\n{sub}" if sub else ""))
            else:
                if sysdeps.IS_MAC:
                    from . import macnotify
                    if macnotify.show(head, sub, body, str(cover) if cover else None):
                        return
                sysdeps.system_notify(head, body, sub, image=str(cover) if cover else None)
        threading.Thread(target=work, daemon=True).start()

    _cover_img = None

    def _tray_message(self, head, body):
        if self.tray is not None:
            self.tray.showMessage(head, body, self.tray.icon(), 4000)

    # ───────────── список відтворення ─────────────
    def rebuild_playlist(self):
        self.table.setRowCount(len(self.playlist))
        for i, p in enumerate(self.playlist):
            t = self.track(p)
            for c, v in enumerate((f"{i + 1}.", t.display, fmt_time(t.length), "")):
                it = QTableWidgetItem(v)
                if c >= 2:
                    it.setTextAlignment((Qt.AlignRight if c == 2 else Qt.AlignCenter) | Qt.AlignVCenter)
                self.table.setItem(i, c, it)
            self._heart_cell(i)
        has = bool(self.playlist)
        self.table.setVisible(has)
        self.pl_empty.setVisible(not has)
        total = sum(self.track(p).length for p in self.playlist)
        self.pl_count.setText(f"{n_tracks(len(self.playlist))} · {fmt_time(total)}" if has else "")
        self.mark_current()
        self.apply_filter(self.search.text())
        if self.player is not None:
            self.spawn(self.refresh_preload())

    def _heart_cell(self, i: int):
        """♥ — у улюблених; ♡ — лише на рядку під курсором чи виділеному (щоб список не рябів)."""
        it = self.table.item(i, 3) if 0 <= i < self.table.rowCount() else None
        if it is None or i >= len(self.playlist):
            return
        fav = self.is_fav(self.playlist[i])
        show_empty = i in (self.table.hover_row, self.table.currentRow())
        it.setText("♥" if fav else ("♡" if show_empty else ""))
        it.setForeground(QColor("#e0245e") if fav else QColor(128, 128, 128))
        it.setToolTip(_("Прибрати з улюблених (F)") if fav else _("До улюблених (F)"))

    def _like_row(self, i: int):
        if 0 <= i < len(self.playlist):
            self.like(self.playlist[i])

    def like(self, path: str | None = None):
        """Лайк / зняти лайк: вибраний рядок у списку (якщо список у фокусі) або те, що грає."""
        if path is None:
            r = self.table.currentRow()
            if self.table.hasFocus() and 0 <= r < len(self.playlist):
                path = self.playlist[r]
            elif 0 <= self.current < len(self.playlist):
                path = self.playlist[self.current]
        state = self.toggle_fav(path)
        if state is None:
            self.toast(_("Спершу увімкніть трек"))
            return
        t = self.track(path)
        self.toast((_("♥ В улюблених: {t}") if state else _("Прибрано з улюблених: {t}")).format(t=t.display))
        for i, p in enumerate(self.playlist):
            if p == path:
                self._heart_cell(i)
        self.update_now_playing()
        if self.tab == "library" or self.tree.topLevelItemCount():
            self.rebuild_tree()

    # ── черга «Грати наступним» ──
    def _selected_paths(self, row: int | None = None) -> list[str]:
        rows = sorted({ix.row() for ix in self.table.selectionModel().selectedRows()})
        if row is not None and row not in rows:
            rows = [row]
        return [self.playlist[r] for r in rows if 0 <= r < len(self.playlist)]

    def play_next(self, paths: list[str] | None = None):
        """Shift+N: виділені рядки списку або вузол медіатеки — заграють одразу після поточного."""
        if paths is None:
            if self.tree.hasFocus() and self.tree.currentItem() is not None:
                paths = self.item_paths(self.tree.currentItem())
            else:
                paths = self._selected_paths()
        if not paths:
            self.toast(_("Виберіть трек у списку або в медіатеці"))
            return
        before = len(self.playlist)
        n = self.queue_play_next(paths)
        self.toast(_("Наступним: {t}").format(t=self.track(paths[0]).display) if n == 1
                   else _("Наступними: {n}").format(n=n_tracks(n)))
        if len(self.playlist) != before:
            self.rebuild_playlist()
            self.save_cfg()
        else:
            self.mark_current()
            self.spawn(self.refresh_preload())

    def unqueue(self, path: str):
        self.queue_consume(path)
        self.mark_current()
        self.spawn(self.refresh_preload())

    def clear_queue(self):
        n = self.queue_clear()
        self.toast(_("Чергу очищено") if n else _("Черга вже порожня"))
        self.mark_current()
        self.spawn(self.refresh_preload())

    def play_favorites(self):
        paths = [p for p in self.favs.paths() if p in self.lib.tracks or os.path.exists(real_path(p))]
        if not paths:
            self.toast(_("Улюблених поки немає — вподобайте трек сердечком або клавішею F"))
            return
        self.add_to_playlist(paths, replace=True)
        self.spawn(self.play_index(random.randrange(len(paths)) if self.shuffle else 0))
        self.toast(_("Грають улюблені: {n}").format(n=n_tracks(len(paths))))

    def export_favorites(self):
        if not len(self.favs):
            self.toast(_("Улюблених поки немає"))
            return
        dest, _f = QFileDialog.getSaveFileName(self, _("Зберегти улюблені як M3U"),
                                               str(Path.home() / _("Улюблені.m3u")), "M3U (*.m3u *.m3u8)")
        if dest:
            try:
                n = self.favs.export_m3u(dest, self.track)
                self.toast(_("Збережено: {n} у {f}").format(n=n_tracks(n), f=Path(dest).name))
            except OSError as e:
                self.toast(_("Не вдалося зберегти: {e}").format(e=e))

    def find_duplicates(self):
        if not self.lib.tracks and not self.playlist:
            self.toast(_("Спершу додайте музику"))
            return
        DuplicatesDialog(self).exec()

    def copy_playlist(self):
        if not self.playlist:
            self.toast(_("Список відтворення порожній"))
            return
        start = next((d for d in ("/Volumes", f"/media/{os.environ.get('USER', '')}", "/media", "/run/media")
                      if os.path.isdir(d) and os.listdir(d)), str(Path.home()))
        dest = QFileDialog.getExistingDirectory(self, _("Куди копіювати? Оберіть флешку або теку"), start)
        if dest:
            CopyDialog(self, list(self.playlist), dest).exec()

    def remove_unliked(self, paths: list[str] | None = None, where: str | None = None):
        paths = list(self.playlist) if paths is None else paths
        if not paths:
            self.toast(_("Тут немає треків"))
            return
        RemoveUnlikedDialog(self, paths, where or _("У списку")).exec()

    def mark_current(self):
        if not hasattr(self, "_acc"):
            return
        sub = QColor(self._sub) if not self._sub.startswith("rgba") else QColor(128, 128, 128)
        sk = self.skin
        a = QColor(self._acc)
        # як позначено рядок, що грає: класичний — жирний текст кольору обкладинки,
        # macOS — суцільна плашка цього кольору, Windows 11 — легка плашка й риска зліва
        cur_fg = QColor(self._on_acc) if sk == "mac" else QColor(self._fg) if sk == "fluent" else a
        for i in range(self.table.rowCount()):
            cur = i == self.current
            for c in range(4):           # колонка 3 — сердечко: колір не чіпаємо, лише тло
                it = self.table.item(i, c)
                if it is None:
                    continue
                if c == 3:
                    continue
                f = QFont(self.table.font())
                f.setBold(cur and sk != "mac")
                if cur and sk == "mac":
                    f.setWeight(QFont.DemiBold)
                it.setFont(f)
                if cur:
                    it.setForeground(cur_fg)
                else:
                    it.setForeground(sub if c != 1 else self.palette().text().color())
            num = self.table.item(i, 0)
            if num is not None:
                k = 0 if cur or i >= len(self.playlist) else self.queue_pos(self.playlist[i])
                num.setText(("▶ " if cur and sk != "fluent" else f"→{k} " if k else "") + f"{i + 1}.")
                num.setToolTip(_("У черзі: {k}-й").format(k=k) if k else "")
                if k:
                    num.setForeground(QColor(self._acc))
        self.table.viewport().update()
        if 0 <= self.current < self.table.rowCount():
            self.table.scrollToItem(self.table.item(self.current, 0), QAbstractItemView.EnsureVisible)

    def add_to_playlist(self, paths, play=False, replace=False):
        paths = [p for p in paths if isinstance(p, str)]
        if not paths:
            return
        if replace:
            self.playlist = list(paths)
            self.current = -1
            self.history = []
            start = 0
        else:
            start = len(self.playlist)
            self.playlist.extend(paths)
        self.rebuild_playlist()
        self.save_cfg()
        if play:
            self.spawn(self.play_index(start))

    def remove_selected(self):
        if self.tab != "playlist":
            return
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            del self.playlist[r]
            if r < self.current:
                self.current -= 1
            elif r == self.current:
                self.current = -1
        self.history = []
        self.rebuild_playlist()
        self.save_cfg()

    def drop_from_playlist(self, gone: set):
        """Прибрати треки зі списку, не збиваючи поточний."""
        if not gone:
            return
        cur = self.playlist[self.current] if 0 <= self.current < len(self.playlist) else None
        self.playlist = [p for p in self.playlist if p not in gone]
        self.current = self.playlist.index(cur) if cur in self.playlist else -1
        self.history = []
        self.rebuild_playlist()
        self.update_now_playing()
        self.save_cfg()

    def clear_playlist(self):
        self.playlist = []
        self.current = -1
        self.history = []
        self.spawn(self.stop())
        self.rebuild_playlist()
        self.update_now_playing()
        self.save_cfg()

    def _table_menu(self, pos):
        r = self.table.rowAt(pos.y())
        m = QMenu(self)
        if r >= 0:
            m.addAction(_("Грати"), lambda: self.spawn(self.play_index(r)))
            if r < len(self.playlist) and self.queue_pos(self.playlist[r]):
                m.addAction(_("Прибрати з черги"), lambda: self.unqueue(self.playlist[r]))
            else:
                m.addAction(_("Грати наступним"), lambda: self.play_next(self._selected_paths(r)))
            if r < len(self.playlist):
                m.addAction(_("Знайти обкладинку…"), lambda: self.pick_cover(self.playlist[r]))
            fav = self.is_fav(self.playlist[r]) if r < len(self.playlist) else False
            m.addAction(_("Прибрати з улюблених") if fav else _("До улюблених"), lambda: self._like_row(r))
            m.addAction(_("Прибрати зі списку"), self.remove_selected)
            m.addSeparator()
        m.addAction(_("Прибрати неулюблені…"), lambda: self.remove_unliked())
        if self.queue:
            m.addAction(_("Очистити чергу"), self.clear_queue)
        if self.playlist:
            m.addAction(_("Копіювати список на флешку…"), self.copy_playlist)
        m.addAction(_("Очистити список"), self.clear_playlist)
        m.exec(self.table.viewport().mapToGlobal(pos))

    # ───────────── медіатека ─────────────
    def set_lib_mode(self, mode: str, rebuild=True):
        self.lib_mode = mode if mode in ("artists", "folders") else "artists"
        for b, m in ((self.mode_art, "artists"), (self.mode_dir, "folders")):
            b.setProperty("on", m == self.lib_mode)
            b.style().unpolish(b)
            b.style().polish(b)
        if rebuild:
            self.rebuild_tree()
            self.save_cfg()

    def rebuild_tree(self):
        tree = self.tree
        tree.clear()
        has = bool(self.lib.tracks)
        tree.setVisible(has)
        self.lib_empty.setVisible(not has)
        if self.scanning and not has:
            self.lib_empty.setText(_("Сканую медіатеку…"))
        n = len(self.lib.tracks)
        self.lib_count.setText(n_tracks(n) if n else "")
        if not has:
            return
        dim = QColor(128, 128, 128)

        def item(parent, text, extra, data):
            it = QTreeWidgetItem(parent, [text, extra])
            it.setData(0, Qt.UserRole, data)
            it.setForeground(1, dim)
            return it

        # розумні списки — нагорі, над виконавцями й теками
        for key, title, paths in self.smart_lists(self.lib.tracks):
            if key != "favorites" and not paths:
                continue
            node = item(tree, ("♥ " if key == "favorites" else "◦ ") + title, str(len(paths)), ("smart", paths))
            if key == "favorites":
                node.setForeground(0, QColor("#e0245e"))
            f = node.font(0)
            f.setBold(key == "favorites")
            node.setFont(0, f)
            for p in paths:
                t = self.track(p)
                item(node, t.display, fmt_time(t.length), ("track", p))
            if key == "favorites" and not paths:
                hint = item(node, _("Вподобайте трек сердечком або клавішею F"), "", None)
                hint.setForeground(0, dim)
        sep = item(tree, "", "", None)
        sep.setFlags(Qt.NoItemFlags)

        if self.lib_mode == "artists":
            artists: dict[str, dict[str, list[Track]]] = {}
            for t in self.lib.tracks.values():
                a = t.albumartist or t.artist or _("Без тегів")
                alb = t.album or Path(t.path).parent.name
                artists.setdefault(a, {}).setdefault(alb, []).append(t)
            for a in sorted(artists, key=lambda s: (s == _("Без тегів"), s.lower())):
                albums = artists[a]
                an = item(tree, a, str(sum(len(v) for v in albums.values())), None)
                all_paths = []
                for alb in sorted(albums, key=lambda k: (min((x.year for x in albums[k]), default="") or "9999", k.lower())):
                    tracks = sorted(albums[alb], key=lambda t: t.sort_key)
                    year = next((x.year for x in tracks if x.year), "")
                    al = item(an, alb, year, ("group", [t.path for t in tracks]))
                    for t in tracks:
                        num = f"{t.track:>2}. " if t.track else ""
                        item(al, num + (t.title or Path(t.path).stem), fmt_time(t.length), ("track", t.path))
                    all_paths.extend(t.path for t in tracks)
                an.setData(0, Qt.UserRole, ("group", all_paths))
        else:
            for root in self.lib.folders:
                tracks = self.lib.under(root)
                rn = item(tree, Path(root).name or root, str(len(tracks)), ("group", [t.path for t in tracks]))
                nodes = {root.rstrip(os.sep): rn}
                for t in tracks:
                    d = os.path.dirname(t.path)
                    if d not in nodes:
                        cur = root.rstrip(os.sep)
                        for part in Path(d).relative_to(root).parts:
                            nxt = os.path.join(cur, part)
                            if nxt not in nodes:
                                nodes[nxt] = item(nodes[cur], part, "", ("group", []))
                            cur = nxt
                    item(nodes[d], t.title if t.segment else Path(t.path).stem, fmt_time(t.length), ("track", t.path))
                for d, node in nodes.items():
                    if node is not rn:
                        pre = d + os.sep
                        node.setData(0, Qt.UserRole, ("group", [t.path for t in tracks if t.path.startswith(pre)]))
                if len(self.lib.folders) == 1:
                    rn.setExpanded(True)
        self.apply_filter(self.search.text())

    @staticmethod
    def item_paths(it) -> list[str]:
        data = it.data(0, Qt.UserRole) if it is not None else None
        if not data:
            return []
        return [data[1]] if data[0] == "track" else list(data[1] or [])

    def lib_activate(self, it):
        data = it.data(0, Qt.UserRole)
        if not data:
            return
        if data[0] == "track":
            parent = it.parent()
            paths = self.item_paths(parent) if parent is not None else [data[1]]
            if data[1] not in paths:
                paths = [data[1]]
            self.add_to_playlist(paths, replace=True)
            self.spawn(self.play_index(paths.index(data[1])))
        else:
            self.add_to_playlist(self.item_paths(it), play=True, replace=True)
        self.toast(_("Грає: {what}").format(what=it.text(0)))

    def lib_append(self):
        paths = []
        for it in self.tree.selectedItems():
            paths.extend(p for p in self.item_paths(it) if p not in paths)
        if paths:
            self.add_to_playlist(paths)
            self.toast(_("Додано в кінець списку: {n}").format(n=n_tracks(len(paths))))

    def lib_all(self):
        if not self.lib.tracks:
            self.toast(_("Медіатека порожня — додайте теку клавішею L"))
            return
        paths, seen = [], set()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            if (top.data(0, Qt.UserRole) or ("",))[0] == "smart":
                continue                          # розумні списки — це ті самі треки, їх не дублюємо
            for p in self.item_paths(top):
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        start = random.randrange(len(paths)) if self.shuffle else 0
        self.add_to_playlist(paths, replace=True)
        self.spawn(self.play_index(start))
        self.toast(_("У списку вся медіатека: {n}").format(n=n_tracks(len(paths))))

    def _tree_menu(self, pos):
        it = self.tree.itemAt(pos)
        m = QMenu(self)
        if it is not None:
            m.addAction(_("Грати"), lambda: self.lib_activate(it))
            m.addAction(_("Додати в кінець списку"), self.lib_append)
            m.addAction(_("Грати наступним"), lambda: self.play_next(self.item_paths(it)))
            data = it.data(0, Qt.UserRole)
            if data and data[0] == "track":
                fav = self.is_fav(data[1])
                m.addAction(_("Прибрати з улюблених") if fav else _("До улюблених"), lambda: self.like(data[1]))
            elif data and data[0] in ("group", "smart"):
                m.addAction(_("Прибрати неулюблені…"),
                            lambda: self.remove_unliked(self.item_paths(it), _("У «{name}»").format(name=it.text(0).lstrip("♥◦ "))))
            m.addSeparator()
        m.addAction(_("Уся медіатека в список"), self.lib_all)
        m.addAction(_("Знайти дублікати…"), self.find_duplicates)
        m.addAction(_("Пересканувати"), self.start_scan)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ───────────── теки ─────────────
    def add_library_folder(self):
        d = QFileDialog.getExistingDirectory(self, _("Додати теку до медіатеки"),
                                             str(Path.home() / "Music") if (Path.home() / "Music").is_dir() else str(Path.home()))
        if d:
            self.add_folders_to_library([d])

    def add_folders_to_library(self, paths):
        added = [p for p in paths if os.path.isdir(p) and p not in self.lib.folders]
        if not added:
            return
        self.lib.folders.extend(added)
        self.save_cfg()
        self.start_scan()
        self.set_tab("library")

    def remove_folders(self, paths):
        for p in paths:
            if p in self.lib.folders:
                self.lib.folders.remove(p)
        pre = tuple(p.rstrip(os.sep) + os.sep for p in paths)
        self.lib.tracks = {k: v for k, v in self.lib.tracks.items() if not k.startswith(pre)}
        self.lib.save()
        self.rebuild_tree()
        self.save_cfg()

    def manage_folders(self):
        FoldersDialog(self).exec()

    def add_playlist_folder(self):
        d = QFileDialog.getExistingDirectory(self, _("Теку — у список відтворення"), str(Path.home()))
        if d:
            paths = sorted(scan_dir(d), key=lambda p: (os.path.dirname(p).lower(), self.track(p).sort_key))
            self.add_to_playlist(paths, play=not self.playlist)
            self.toast(_("Додано в кінець списку: {n}").format(n=n_tracks(len(paths))))

    def start_scan(self):
        if self.scanning:
            return
        self.scanning = True
        self.lib_count.setText(_("сканую…"))

        def work():
            def progress(i, total):
                self.call_from_thread(lambda: self.lib_count.setText(_("сканую {i} з {total}…").format(i=i, total=total)))
            try:
                self.lib.scan(progress)
            except Exception as e:
                log(f"scan: {e}")
            self.call_from_thread(self._scan_done)
        threading.Thread(target=work, daemon=True).start()

    def _scan_done(self):
        self.scanning = False
        try:
            if self.favs.relink(self.lib.tracks):
                self.toast(_("Улюблені знайдено на новому місці — лайки збережено"))
        except Exception as e:
            log(f"улюблені: {e}")
        self.lib_empty.setText(_("Медіатека порожня.\n\nДодайте теку з музикою кнопкою «+ Тека» "
                                 "або просто перетягніть теку у вікно."))
        self.rebuild_tree()
        self.rebuild_playlist()

    # ───────────── пошук ─────────────
    def apply_filter(self, text: str):
        q = (text or "").strip().lower()
        if self.tab == "playlist":
            for i in range(self.table.rowCount()):
                it = self.table.item(i, 1)
                self.table.setRowHidden(i, bool(q) and (it is None or q not in it.text().lower()))
        else:
            def walk(it) -> bool:
                own = q in it.text(0).lower()
                kids = [walk(it.child(k)) for k in range(it.childCount())]
                show = not q or own or any(kids)
                if own and q:      # збіг на виконавці/альбомі — показати все всередині
                    for k in range(it.childCount()):
                        self._unhide(it.child(k))
                it.setHidden(not show)
                if q and any(kids):
                    it.setExpanded(True)
                return show
            for i in range(self.tree.topLevelItemCount()):
                walk(self.tree.topLevelItem(i))

    def _unhide(self, it):
        it.setHidden(False)
        for k in range(it.childCount()):
            self._unhide(it.child(k))

    def search_enter(self):
        if self.tab == "playlist":
            for i in range(self.table.rowCount()):
                if not self.table.isRowHidden(i):
                    self.spawn(self.play_index(i))
                    break
        else:
            it = self.tree.topLevelItem(0)
            while it is not None and it.isHidden():
                it = self.tree.itemBelow(it)
            if it is not None:
                self.tree.setCurrentItem(it)
                self.tree.setFocus()

    # ───────────── перетягування ─────────────
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        folders, files = [], []
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if os.path.isdir(p):
                folders.append(p)
            elif Path(p).suffix.lower() in AUDIO_EXT:
                files.append(p)
        if folders:
            self.add_folders_to_library(folders)
        if files:
            self.add_to_playlist(files, play=not self.playlist)

    # ───────────── система ─────────────
    def setup_platform(self):
        if sysdeps.IS_MAC and not self.demo:
            try:
                from . import macnotify
                log(f"macnotify: {macnotify.init()}")
            except Exception as e:
                log(f"macnotify: {e}")
        if QSystemTrayIcon.isSystemTrayAvailable() and not os.environ.get("PLATIVKA_NO_TRAY"):
            self.tray = QSystemTrayIcon(app_icon(), self)
            m = QMenu()
            m.addAction(_("Показати плеєр"), self.show_from_tray)
            m.addSeparator()
            m.addAction(_("Грати / пауза"), self.toggle_from_tray)
            m.addAction(_("Наступний трек"), self.next_from_tray)
            m.addAction(_("Попередній трек"), self.prev_from_tray)
            m.addAction(_("До улюблених / прибрати"), lambda: self.like())
            m.addSeparator()
            m.addAction(_("Вийти з Платівки"), self.quit_app)
            self.tray.setContextMenu(m)
            self._tray_menu = m
            self.tray.activated.connect(lambda r: self.show_from_tray()
                                        if r == QSystemTrayIcon.Trigger and not sysdeps.IS_MAC else None)
            self.tray.show()
        if sysdeps.IS_WIN and not self.demo:
            try:
                from .smtc import Smtc
                sm = Smtc(self)
                if sm.start():
                    self.smtc = sm
            except Exception as e:
                log(f"smtc: {e}")
        if sysdeps.IS_LINUX and not self.demo:
            self.spawn(self._start_mpris())

    async def _start_mpris(self):
        try:
            from .mpris import Mpris
            m = Mpris(self)
            if await m.start():
                self.mpris = m
        except Exception as e:
            log(f"mpris: {e}")

    def _platform_tick(self):
        cur = self.track(self.playlist[self.current]) if 0 <= self.current < len(self.playlist) else None
        for x in (self.mpris, self.smtc):
            if x is not None:
                try:
                    x.refresh(cur, self._cover_file)
                except Exception:
                    pass

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def open_url(self, url: str):
        QDesktopServices.openUrl(url)

    def about(self):
        QMessageBox.about(self, _("Про Платівку"), f"<h3>{APP_NAME} {VERSION}</h3>"
                          + "<p>" + _("Музичний плеєр у дусі Winamp для macOS, Windows і Linux.") + "</p>"
                          + "<p>" + _("Автор: {a}").format(a=AUTHOR) + "<br>"
                          + f'<a href="{GITHUB_URL}">{GITHUB_URL}</a></p>'
                          + "<p>" + _("Ліцензія MIT. Звук — mpv, інтерфейс — Qt.") + "</p>")

    def toggle_language(self):
        new = "en" if LANG == "uk" else "uk"
        self.cfg["lang"] = new
        self.save_cfg()
        QMessageBox.information(self, APP_NAME, _("Мову буде змінено після перезапуску Платівки."))

    def closeEvent(self, e):
        if self.minimize_to_tray and self.tray is not None and not self._quitting:
            e.ignore()
            self.hide()
            return
        self.quit_app()
        e.accept()

    def quit_app(self):
        if self._quitting:
            return
        self._quitting = True
        self.save_cfg()
        for x in (self.smtc, self.mpris):
            try:
                if x is not None:
                    x.stop()
            except Exception:
                pass
        if self.tray is not None:
            self.tray.hide()

        async def bye():
            self.end_listen()
            try:
                if self.remote:
                    await asyncio.wait_for(self.remote.stop(), 2)
            except Exception:
                pass
            try:
                if self.player:
                    await asyncio.wait_for(self.player.close(), 2)
            except Exception:
                pass
            QApplication.quit()
        self.spawn(bye())


# ═══════════════════════════════ запуск ═══════════════════════════════
def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return
    import qasync
    rotate_log()
    log(f"--- старт {APP_NAME} desktop {VERSION}")
    QApplication.setApplicationName("Plativka")
    QApplication.setApplicationDisplayName(APP_NAME)
    QApplication.setOrganizationName("Plativka")
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    if sysdeps.IS_WIN:
        app.setStyle("Fusion")
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dkindratyuk.Plativka.Desktop")
            from . import winnotify
            winnotify.use_desktop_app()
        except Exception:
            pass
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = MainWindow(demo="--demo" in sys.argv)
    win.show()
    t1 = QTimer(win)
    t1.timeout.connect(win.tick)
    t1.start(250)
    t2 = QTimer(win)
    t2.timeout.connect(lambda: asyncio.ensure_future(win.vu_tick()))
    t2.start(100)
    t3 = QTimer(win)
    t3.timeout.connect(win.save_cfg)
    t3.start(5000)
    app.aboutToQuit.connect(win.save_cfg)

    async def boot():
        await win.start_player()
        if win.lib.folders:
            win.start_scan()
        if win.remote_cfg.get("enabled"):
            await win.set_remote(True)
        if not win.demo:
            await asyncio.sleep(3)
            while True:             # і далі, поки Платівка відкрита, — раз на 6 годин
                if win.check_updates:
                    await win.look_for_update()
                await asyncio.sleep(UPDATE_EVERY)
    with loop:
        loop.create_task(boot())
        loop.run_forever()


if __name__ == "__main__":
    main()
