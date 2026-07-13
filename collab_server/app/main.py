"""
MyoOptix Collab Edition — entry point.

Startup flow:
  1. Load saved token from disk
  2. Try /auth/verify in background thread
     → valid: show Quick Analysis
     → expired/invalid: show Login
     → network error: show error dialog
  3. No token: show Login
"""

import sys
from pathlib import Path

APP_DIR  = Path(__file__).parent
REPO_ROOT = APP_DIR.parent.parent   # myooptix/ repo root — contains cardio_py/
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon

from ui.style import build_style
from ui.dialog_login import LoginDialog
from ui.dialog_quick import QuickAnalysisDialog
import token_store
from api_client import verify, APIError


def _assets() -> str:
    return str(APP_DIR / "assets")


class _VerifyWorker(QThread):
    ok      = pyqtSignal(dict)   # user_info
    expired = pyqtSignal()
    network_err = pyqtSignal(str)

    def __init__(self, token):
        super().__init__()
        self.token = token

    def run(self):
        try:
            info = verify(self.token)
            self.ok.emit(info)
        except APIError as e:
            if "cannot reach" in str(e).lower() or "unreachable" in str(e).lower():
                self.network_err.emit(str(e))
            else:
                self.expired.emit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MyoOptix")
    app.setStyleSheet(build_style(_assets()))

    icon_path = APP_DIR / "assets" / "icon.png"
    if not icon_path.exists():
        icon_path = APP_DIR / "assets" / "heart.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    _refs = []  # keep references to prevent GC

    def show_login():
        print("[main] showing login dialog")
        login_dlg = LoginDialog()
        _refs.append(login_dlg)

        def on_logged_in(tok: str, em: str):
            print(f"[main] logged in as {em}, verifying…")
            token_store.save(tok, em)
            w = _VerifyWorker(tok)
            _refs.append(w)

            def on_ok(info):
                print(f"[main] verify OK: {info}")
                open_main(tok, info)
                login_dlg.accept()
            def on_fail():
                print("[main] verify failed, using basic info")
                open_main(tok, {"email": em, "full_name": em, "institution": ""})
                login_dlg.accept()
            def on_net(msg):
                print(f"[main] verify network error: {msg}")
                open_main(tok, {"email": em, "full_name": em, "institution": ""})
                login_dlg.accept()

            w.ok.connect(on_ok)
            w.expired.connect(on_fail)
            w.network_err.connect(on_net)
            w.start()

        login_dlg.logged_in.connect(on_logged_in)
        login_dlg.rejected.connect(app.quit)
        login_dlg.show()
        print("[main] login dialog shown")

    def open_main(tok, user_info):
        print(f"[main] opening QuickAnalysisDialog for {user_info}")
        dlg = QuickAnalysisDialog(token=tok, user_info=user_info)
        dlg.setWindowTitle("MyoOptix")

        def on_finished(result):
            # if token was cleared (logout), go back to login
            saved_tok, _ = token_store.load()
            if not saved_tok:
                show_login()
            else:
                app.quit()

        dlg.finished.connect(on_finished)
        _refs.append(dlg)
        dlg.show()
        print("[main] QuickAnalysisDialog shown")

    # ── try saved token ───────────────────────────────────────────────────────
    token, _ = token_store.load()
    if token:
        worker = _VerifyWorker(token)
        _refs.append(worker)

        def on_verify_ok(info):
            open_main(token, info)

        def on_verify_expired():
            token_store.clear()
            show_login()

        def on_verify_network(msg):
            ret = QMessageBox.warning(
                None, "Network Error",
                "Cannot connect to MyoOptix server.\n\n"
                "Please check your internet connection and try again.",
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Retry:
                token_store.clear()
                show_login()
            else:
                app.quit()

        worker.ok.connect(on_verify_ok)
        worker.expired.connect(on_verify_expired)
        worker.network_err.connect(on_verify_network)
        worker.start()
    else:
        show_login()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

