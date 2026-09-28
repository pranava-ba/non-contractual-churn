"""PyQt6 WebEngine desktop app: a Refresh button + status banner over a browsable,
week-filterable view of the tracker DB. Run with `python -m gui`."""
from __future__ import annotations

import json
import os
import sys
import warnings

# Under pythonw.exe (launched from a desktop shortcut, no console) sys.stdout /
# sys.stderr are None, so the app's print()s would crash. Redirect to null.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

warnings.filterwarnings("ignore", message="urllib3")  # harmless version-mismatch notice

# Force software rendering for the web view (GPU compositing of a fixed gradient
# under scrolling content flickers on some Windows drivers) and quiet Chromium's
# GPU-probe ERROR spam. Must be set before any QtWebEngine import.
_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (_flags + " --disable-gpu --log-level=3").strip()

from PyQt6.QtCore import Qt, QFile, QIODevice, QObject, QRunnable, QThreadPool, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

from src.config import load_config
from src import run as runner, store, downloader
from . import data, page


def _qwebchannel_js() -> str:
    """Read Qt's bundled qwebchannel.js so we can inline it (robust vs. qrc loads)."""
    f = QFile(":/qtwebchannel/qwebchannel.js")
    if f.open(QIODevice.OpenModeFlag.ReadOnly):
        try:
            return bytes(f.readAll()).decode("utf-8")
        finally:
            f.close()
    return ""


class _TaskSignals(QObject):
    done = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)


class _RefreshTask(QRunnable):
    """Runs a full refresh off the UI thread, then returns a fresh snapshot JSON."""

    def __init__(self, cfg, signals: "_TaskSignals", source: str = "all"):
        super().__init__()
        self.cfg = cfg
        self.signals = signals
        self.source = source

    def run(self):
        snap = data.snapshot(self.cfg)  # fallback = current data if refresh fails
        try:
            result = runner.run(source=self.source,
                                on_progress=lambda d, t, label: self.signals.progress.emit(d, t, label))
            snap = data.snapshot(self.cfg)
            if result.get("errors"):
                snap["error"] = (f"{result['errors']} feed(s) failed — likely an OpenAlex "
                                 "rate limit. Wait a while, then refresh again.")
        except Exception as e:  # surface, don't crash the app
            snap["error"] = str(e)
        self.signals.done.emit(json.dumps(snap))


class _DownloadSignals(QObject):
    done = pyqtSignal(str)


class _DownloadTask(QRunnable):
    def __init__(self, cfg, uid, signals):
        super().__init__()
        self.cfg, self.uid, self.signals = cfg, uid, signals

    def run(self):
        out = {"ok": False, "uid": self.uid}
        conn = store.connect(self.cfg.path("db_path"))
        try:
            row = store.get_paper(conn, self.uid)
        finally:
            conn.close()
        if not row:
            out["error"] = "paper not found"
            self.signals.done.emit(json.dumps(out)); return
        paper = {"arxiv_id": row["arxiv_id"], "doi": row["doi"],
                 "oa_url": row["oa_url"], "title": row["title"]}
        try:
            path, src = downloader.download_paper(
                paper, self.cfg.path("download_dir"),
                self.cfg.settings.get("scihub_mirrors") or [],
                self.cfg.settings.get("proxy") or None,
                contact_email=self.cfg.settings.get("contact_email"),
                unpaywall_enabled=self.cfg.settings.get("unpaywall_enabled", True))
            out.update(ok=True, path=str(path), source=src, title=row["title"])
        except Exception as e:
            out["error"] = str(e)
        self.signals.done.emit(json.dumps(out))


class Backend(QObject):
    refreshStarted = pyqtSignal()
    refreshFinished = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)  # done, total, label
    downloaded = pyqtSignal(str)          # json: ok/path/source/title/error

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._busy = False
        self._pool = QThreadPool.globalInstance()

    @pyqtSlot(result=str)
    def snapshot(self) -> str:
        return json.dumps(data.snapshot(self.cfg))

    @pyqtSlot(str)
    def refresh(self, source: str = "all"):
        if self._busy:
            return
        self._busy = True
        self.refreshStarted.emit()
        sig = _TaskSignals()
        sig.done.connect(self._on_done)
        sig.progress.connect(self.progress)  # forward progress to the page
        self._sig = sig  # keep a reference alive
        self._pool.start(_RefreshTask(self.cfg, sig, source or "all"))

    def _on_done(self, snapshot_json: str):
        self._busy = False
        self.refreshFinished.emit(snapshot_json)

    @pyqtSlot(str)
    def openUrl(self, url: str):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @pyqtSlot(str)
    def copyToClipboard(self, text: str):
        QApplication.clipboard().setText(text or "")

    @pyqtSlot(str, bool)
    def setRead(self, uid: str, value: bool):
        self._set_state(uid, "read", value)

    @pyqtSlot(str, bool)
    def setStarred(self, uid: str, value: bool):
        self._set_state(uid, "starred", value)

    @pyqtSlot(str, bool)
    def setHidden(self, uid: str, value: bool):
        self._set_state(uid, "hidden", value)

    @pyqtSlot(str, bool)
    def setAnalyzed(self, uid: str, value: bool):
        self._set_state(uid, "analyzed", value)

    @pyqtSlot(str, int)
    def setUsedOverride(self, uid: str, value: int):
        """value: 1 (force used), 0 (force not-used), -1 (clear -> auto-detect)."""
        conn = store.connect(self.cfg.path("db_path"))
        try:
            store.set_used_override(conn, uid, None if value < 0 else bool(value))
        finally:
            conn.close()

    @pyqtSlot(str, str)
    def setTags(self, uid: str, tags: str):
        conn = store.connect(self.cfg.path("db_path"))
        try:
            store.set_tags(conn, uid, tags)
        finally:
            conn.close()

    def _set_state(self, uid, field, value):
        conn = store.connect(self.cfg.path("db_path"))
        try:
            store.set_state(conn, uid, field, value)
        finally:
            conn.close()

    @pyqtSlot(str)
    def downloadPaper(self, uid: str):
        sig = _DownloadSignals()
        sig.done.connect(self._on_download)
        self._pool.start(_DownloadTask(self.cfg, uid, sig))

    def _on_download(self, result_json: str):
        self.downloaded.emit(result_json)
        try:
            res = json.loads(result_json)
            if res.get("ok") and res.get("path"):
                QDesktopServices.openUrl(QUrl.fromLocalFile(res["path"]))
        except Exception:
            pass

    @pyqtSlot()
    def quit(self):
        QApplication.quit()


def main():
    cfg = load_config()
    app = QApplication(sys.argv)
    app.setApplicationName("Research Paper Tracker")

    backend = Backend(cfg)
    channel = QWebChannel()
    channel.registerObject("backend", backend)

    view = QWebEngineView()
    # A named profile persists to disk, so the page's localStorage (remembered
    # tab / category / sidebar state) survives app restarts.
    profile = QWebEngineProfile("papertracker", app)
    web_page = QWebEnginePage(profile, view)
    # Opaque, theme-matched page background prevents white/transparent flashes
    # (a common QtWebEngine flicker source) during load and repaints.
    try:
        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        dark = True
    web_page.setBackgroundColor(QColor("#0e0f1e" if dark else "#EEF0FB"))
    view.setPage(web_page)
    view.page().setWebChannel(channel)
    # https base gives a secure origin so Google Fonts can load (falls back to
    # system fonts offline). qwebchannel.js is inlined, so no qrc dependency.
    view.setHtml(page.render_page(_qwebchannel_js()), QUrl("https://papertracker.local/"))

    win = QMainWindow()
    win.setWindowTitle("Research Paper Tracker")
    win.resize(1320, 860)
    win.setCentralWidget(view)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
