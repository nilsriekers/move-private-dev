# qt_helpers.py
"""PyQt6 helper utilities: thread-safe invoker, custom range slider, combo helpers."""
import functools
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QApplication


class _Invoker(QObject):
    """Singleton helper that executes callables on the main GUI thread.

    Must be created on the main thread, and uses QueuedConnection so that
    emits from worker threads are dispatched to the main event loop.
    """
    _call = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        if app is not None:
            self.moveToThread(app.thread())
        self._call.connect(self._execute, Qt.ConnectionType.QueuedConnection)

    @pyqtSlot(object)
    def _execute(self, fn):
        fn()


_invoker_instance = None


def invoke_in_main_thread(fn, *args, **kwargs):
    """Schedule *fn* to run on the main (GUI) thread. Thread-safe."""
    global _invoker_instance
    if _invoker_instance is None:
        _invoker_instance = _Invoker()
    if args or kwargs:
        fn = functools.partial(fn, *args, **kwargs)
    _invoker_instance._call.emit(fn)


def set_combo_items(combo, items, current_text=None):
    """Replace all items in a QComboBox, optionally selecting one."""
    if combo is None:
        return
    combo.blockSignals(True)
    combo.clear()
    combo.addItems(items)
    if current_text is not None:
        idx = combo.findText(current_text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(current_text)
    combo.blockSignals(False)


class RadioAdapter:
    """Wraps a QButtonGroup so that code using .set()/.get() on a tk.StringVar still works."""
    def __init__(self, button_group):
        self._bg = button_group

    def set(self, value):
        btn = self._bg.button(int(value))
        if btn:
            btn.setChecked(True)

    def get(self):
        checked = self._bg.checkedButton()
        if checked:
            return str(self._bg.id(checked))
        return "1"


class QRangeSliderV(QWidget):
    """Vertical dual-handle range slider for spectrogram vmin/vmax control."""
    valuesChanged = pyqtSignal(float, float)

    _TRACK_WIDTH = 6
    _HANDLE_RADIUS = 9
    _MARGIN = 38

    def __init__(self, min_val, max_val, bottom_val, top_val, parent=None):
        super().__init__(parent)
        self._min = float(min_val)
        self._max = float(max_val)
        self._bottom = float(bottom_val)
        self._top = float(top_val)
        self._dragging = None
        self.setMinimumWidth(90)
        self.setMinimumHeight(100)
        self._font = QFont("Arial", 12, QFont.Weight.Bold)

    # -- public API --
    def bottom(self):
        return self._bottom

    def top(self):
        return self._top

    def setBottom(self, v):
        v = max(self._min, min(v, self._top))
        if v != self._bottom:
            self._bottom = v
            self.update()
            self.valuesChanged.emit(self._bottom, self._top)

    def setTop(self, v):
        v = min(self._max, max(v, self._bottom))
        if v != self._top:
            self._top = v
            self.update()
            self.valuesChanged.emit(self._bottom, self._top)

    # -- coordinate helpers --
    def _val_to_y(self, val):
        """Map a value to a y pixel coordinate (top of widget = max, bottom = min)."""
        h = self.height() - 2 * self._MARGIN
        if self._max == self._min:
            return self._MARGIN
        frac = (val - self._min) / (self._max - self._min)
        return self._MARGIN + h * (1.0 - frac)

    def _y_to_val(self, y):
        h = self.height() - 2 * self._MARGIN
        if h <= 0:
            return self._min
        frac = 1.0 - (y - self._MARGIN) / h
        return self._min + frac * (self._max - self._min)

    # -- painting --
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(self._font)
        fm = QFontMetrics(self._font)
        cx = self.width() // 2

        # track
        track_top = self._MARGIN
        track_bot = self.height() - self._MARGIN
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(200, 200, 200))
        p.drawRoundedRect(cx - self._TRACK_WIDTH // 2, track_top,
                          self._TRACK_WIDTH, track_bot - track_top,
                          self._TRACK_WIDTH // 2, self._TRACK_WIDTH // 2)

        # selected range highlight
        y_bot = self._val_to_y(self._bottom)
        y_top = self._val_to_y(self._top)
        p.setBrush(QColor(80, 130, 200))
        p.drawRect(cx - self._TRACK_WIDTH // 2, int(y_top),
                   self._TRACK_WIDTH, int(y_bot - y_top))

        # handles
        for y_pos, color in [(y_bot, QColor(60, 60, 200)), (y_top, QColor(200, 60, 60))]:
            p.setBrush(color)
            p.setPen(QColor(40, 40, 40))
            p.drawEllipse(int(cx - self._HANDLE_RADIUS), int(y_pos - self._HANDLE_RADIUS),
                          self._HANDLE_RADIUS * 2, self._HANDLE_RADIUS * 2)

        # value labels
        p.setPen(QColor(0, 0, 0))
        top_text = f"{self._top:.0f}"
        bot_text = f"{self._bottom:.0f}"
        p.drawText(cx - fm.horizontalAdvance(top_text) // 2,
                   int(y_top - self._HANDLE_RADIUS - 6), top_text)
        p.drawText(cx - fm.horizontalAdvance(bot_text) // 2,
                   int(y_bot + self._HANDLE_RADIUS + fm.height() + 2), bot_text)

        # min / max labels (smaller, grey)
        small_font = QFont("Arial", 9)
        p.setFont(small_font)
        sfm = QFontMetrics(small_font)
        p.setPen(QColor(120, 120, 120))
        max_text = f"{self._max:.0f}"
        min_text = f"{self._min:.0f}"
        p.drawText(cx - sfm.horizontalAdvance(max_text) // 2, sfm.height(), max_text)
        p.drawText(cx - sfm.horizontalAdvance(min_text) // 2, self.height() - 4, min_text)

        p.end()

    # -- mouse interaction --
    def mousePressEvent(self, event):
        y = event.position().y()
        y_bot = self._val_to_y(self._bottom)
        y_top = self._val_to_y(self._top)
        dist_bot = abs(y - y_bot)
        dist_top = abs(y - y_top)
        threshold = self._HANDLE_RADIUS * 2.5
        if dist_bot < threshold or dist_top < threshold:
            self._dragging = 'bottom' if dist_bot < dist_top else 'top'

    def mouseMoveEvent(self, event):
        if self._dragging is None:
            return
        val = self._y_to_val(event.position().y())
        val = max(self._min, min(self._max, val))
        if self._dragging == 'bottom':
            val = max(self._min, min(val, self._top))
            if val != self._bottom:
                self._bottom = val
                self.update()
                self.valuesChanged.emit(self._bottom, self._top)
        else:
            val = min(self._max, max(val, self._bottom))
            if val != self._top:
                self._top = val
                self.update()
                self.valuesChanged.emit(self._bottom, self._top)

    def mouseReleaseEvent(self, event):
        self._dragging = None
