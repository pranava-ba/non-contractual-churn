"""QWebChannel bridge — exposes Python to the HTML/JS page as `backend.*`.

Mirrors research-paper-tracker/gui/app.py: network work runs off the UI thread on
a QThreadPool, results come back as JSON over signals. Every @pyqtSlot is callable
from JavaScript.
"""
from __future__ import annotations

import json
import traceback

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QFileDialog

from . import analyze, export, openalex, subdomains


class _WorkerSignals(QObject):
    done = pyqtSignal(str)     # JSON payload
    error = pyqtSignal(str)


class _Worker(QRunnable):
    """Run a plain function off the UI thread; emit its JSON result or the error."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = _WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.done.emit(json.dumps(result))
        except Exception as e:                       # surface, never crash the app
            traceback.print_exc()
            self.signals.error.emit(str(e))


def _search_job(query, year_from, min_citations, limit, journals_only) -> dict:
    papers = openalex.search_core(query, year_from, min_citations, limit, journals_only)
    for p in papers:
        analyze.score(p)
    return {"query": query, "papers": papers}


def _related_job(work_id, n_helpers, n_additional, add_sort) -> dict:
    helpers = openalex.references(work_id, n_helpers)
    additional = openalex.citations(work_id, n_additional, add_sort)
    for p in helpers:
        analyze.score(p)
    for p in additional:
        analyze.score(p)
    return {"work_id": work_id, "helpers": helpers, "additional": additional}


class Backend(QObject):
    searchStarted = pyqtSignal()
    coreResults = pyqtSignal(str)
    relatedStarted = pyqtSignal(str)     # work_id
    relatedResults = pyqtSignal(str)
    failed = pyqtSignal(str)
    exported = pyqtSignal(str)           # saved path, or "" if cancelled/failed

    def __init__(self):
        super().__init__()
        self._pool = QThreadPool.globalInstance()
        self._alive: list[_Worker] = []   # keep refs so workers aren't GC'd mid-run

    # ---- data ---------------------------------------------------------------

    @pyqtSlot(result=str)
    def presets(self) -> str:
        return json.dumps(subdomains.as_json())

    @pyqtSlot(str)
    def searchCore(self, params_json: str):
        try:
            p = json.loads(params_json)
        except Exception:
            self.failed.emit("bad search params")
            return
        query = (p.get("query") or "").strip()
        if not query:
            self.failed.emit("Enter a search query or pick a sub-domain.")
            return
        self.searchStarted.emit()
        year_from = max(int(p.get("yearFrom", openalex.MIN_YEAR)), openalex.MIN_YEAR)
        self._run(
            _Worker(_search_job, query,
                    year_from, int(p.get("minCitations", 20)),
                    int(p.get("limit", 40)), bool(p.get("journalsOnly", True))),
            self.coreResults,
        )

    @pyqtSlot(str)
    def loadRelated(self, params_json: str):
        try:
            p = json.loads(params_json)
        except Exception:
            self.failed.emit("bad related params")
            return
        work_id = p.get("workId")
        if not work_id:
            self.failed.emit("no work id")
            return
        self.relatedStarted.emit(work_id)
        self._run(
            _Worker(_related_job, work_id,
                    int(p.get("nHelpers", 5)), int(p.get("nAdditional", 40)),
                    p.get("addSort", "cited_by_count:desc")),
            self.relatedResults,
        )

    def _run(self, worker: _Worker, done_signal):
        self._alive.append(worker)

        def _finish(payload, w=worker):
            done_signal.emit(payload)
            if w in self._alive:
                self._alive.remove(w)

        def _fail(msg, w=worker):
            self.failed.emit(msg)
            if w in self._alive:
                self._alive.remove(w)

        worker.signals.done.connect(_finish)
        worker.signals.error.connect(_fail)
        self._pool.start(worker)

    # ---- utilities ----------------------------------------------------------

    @pyqtSlot(str)
    def openUrl(self, url: str):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @pyqtSlot(str)
    def copyToClipboard(self, text: str):
        QApplication.clipboard().setText(text or "")

    @pyqtSlot(str, str)
    def exportSelection(self, kind: str, papers_json: str):
        """kind = 'bibtex' | 'csv'. Opens a save dialog on the UI thread."""
        try:
            papers = json.loads(papers_json)
        except Exception:
            self.exported.emit("")
            return
        if kind == "csv":
            text, ext, filt = export.to_csv(papers), "csv", "CSV (*.csv)"
        else:
            text, ext, filt = export.to_bibtex(papers), "bib", "BibTeX (*.bib)"
        path, _ = QFileDialog.getSaveFileName(
            None, "Save references", f"references.{ext}", filt)
        if not path:
            self.exported.emit("")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.exported.emit(path)
        except Exception as e:
            self.failed.emit(f"could not save: {e}")
            self.exported.emit("")

    @pyqtSlot()
    def quit(self):
        QApplication.quit()
