"""PyQt6 WebEngine desktop app. Run with `python run_qt.py` or `python -m explorer`."""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore", message="urllib3")

# Software rendering + quiet Chromium GPU spam — set before any QtWebEngine import
# (same rationale as the tracker: GPU compositing of the fixed gradient flickers).
_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (_flags + " --disable-gpu --log-level=3").strip()

from PyQt6.QtCore import Qt, QFile, QIODevice, QUrl
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .backend import Backend
from . import page


def _qwebchannel_js() -> str:
    """Inline Qt's bundled qwebchannel.js (robust vs. qrc loads)."""
    f = QFile(":/qtwebchannel/qwebchannel.js")
    if f.open(QIODevice.OpenModeFlag.ReadOnly):
        try:
            return bytes(f.readAll()).decode("utf-8")
        finally:
            f.close()
    return ""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Paper Explorer")

    backend = Backend()
    channel = QWebChannel()
    channel.registerObject("backend", backend)

    view = QWebEngineView()
    profile = QWebEngineProfile("paperexplorer", app)   # persists page localStorage
    web_page = QWebEnginePage(profile, view)
    try:
        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        dark = True
    web_page.setBackgroundColor(QColor("#0e0f1e" if dark else "#EEF0FB"))
    view.setPage(web_page)
    view.page().setWebChannel(channel)
    # https origin so Google Fonts can load (falls back to system fonts offline).
    view.setHtml(page.render_page(_qwebchannel_js()), QUrl("https://paperexplorer.local/"))

    win = QMainWindow()
    win.setWindowTitle("Paper Explorer — reproduce & beat a journal paper")
    win.resize(1280, 880)
    win.setCentralWidget(view)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
