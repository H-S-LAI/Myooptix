"""Shared toast notification widget."""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor


# App palette-matched styles
_PRESETS = {
    "loading": ("#6b6456", "#ffffff"),   # warm dark brown
    "info":    ("#5a7a9a", "#ffffff"),   # muted blue
    "success": ("#4a7a52", "#ffffff"),   # muted green
    "warning": ("#8a6a10", "#ffffff"),   # amber
    "error":   ("#8a3030", "#ffffff"),   # muted red
}


class Toast(QLabel):
    """
    Floating toast over the parent widget.
    duration=0  → stays until .close() is called
    duration>0  → auto-dismisses after that many ms
    """

    def __init__(self, message: str, parent=None,
                 kind: str = "info", duration: int = 2400):
        super().__init__(message, parent)
        bg, fg = _PRESETS.get(kind, _PRESETS["info"])
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg};"
            "border-radius: 6px;"
            "padding: 8px 18px;"
            "font-size: 13px;"
            "font-weight: 600;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self.adjustSize()
        self._reposition()
        self._anim = None
        self.show()
        self.raise_()

        # loading toasts (duration=0) skip animation so they appear immediately
        # even when the main thread is blocked
        if duration > 0:
            self._fade(start=0.0, end=1.0, ms=160)
            QTimer.singleShot(duration, self._dismiss)

    def _reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        pw, ph = parent.width(), parent.height()
        tw, th = self.width(), self.height()
        x = (pw - tw) // 2
        y = ph - th - 44
        self.move(max(x, 8), max(y, 8))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()

    def _fade(self, start: float, end: float, ms: int, on_done=None):
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        eff = QGraphicsOpacityEffect(self)
        eff.setOpacity(start)
        self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if on_done:
            anim.finished.connect(on_done)
        anim.start()
        self._anim = anim  # keep reference

    def _dismiss(self):
        self._fade(start=1.0, end=0.0, ms=200, on_done=self.close)

    def close(self):
        # if already fading, just let it finish; else fade out then close
        if self._anim is not None and self._anim.state() == QPropertyAnimation.State.Running:
            super().close()
            return
        self._fade(start=1.0, end=0.0, ms=160, on_done=super().close)
