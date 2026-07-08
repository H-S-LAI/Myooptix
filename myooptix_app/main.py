import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from ui.style import APP_STYLE, build_style
from ui.main_window import MainWindow
from ui.dialog_welcome import WelcomeDialog
import updater

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def _save_config(cfg: dict):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MyoOptix")
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    app.setWindowIcon(QIcon(icon_path))
    assets = os.path.join(os.path.dirname(__file__), "assets")
    app.setStyleSheet(build_style(assets))

    # Check for U-Net weights on first launch
    if not updater.weights_exist():
        from ui.dialog_update import ModelDownloadDialog
        ModelDownloadDialog().exec()  # user can skip; Otsu will be used instead

    # Background update check (silent if no network)
    try:
        from version import VERSION
        info = updater.check_for_update(VERSION)
        if info:
            from ui.dialog_update import UpdateAvailableDialog
            UpdateAvailableDialog(info).exec()
    except Exception:
        pass

    welcome = WelcomeDialog()
    if welcome.exec() != WelcomeDialog.DialogCode.Accepted:
        sys.exit(0)

    mode = welcome.get_mode()

    # ── Quick Analysis: no project, no MainWindow ─────────────────────────────
    if mode == WelcomeDialog.MODE_QUICK:
        from ui.dialog_quick import QuickAnalysisDialog
        dlg = QuickAnalysisDialog()
        dlg.exec()
        # return to welcome screen after Quick Analysis finishes
        main()
        return

    video_root   = ""
    project_root = ""
    project_name = ""

    if mode == WelcomeDialog.MODE_NEW:
        from ui.dialog_new_project import NewProjectDialog
        dlg = NewProjectDialog()
        if dlg.exec() != NewProjectDialog.DialogCode.Accepted:
            sys.exit(0)
        project_root = dlg.project_root
        project_name = Path(project_root).name
        video_root   = dlg.video_root or str(Path(project_root).parent)

        if dlg.load_mode == NewProjectDialog.LOAD_IMPORT:
            from ui.dialog_import import ImportDialog
            imp = ImportDialog(project_root=str(Path(project_root).parent))
            if imp.exec() != ImportDialog.DialogCode.Accepted:
                sys.exit(0)
            video_root = str(Path(project_root).parent)

    else:  # MODE_OPEN
        from ui.dialog_open_project import OpenProjectDialog
        dlg = OpenProjectDialog()
        if dlg.exec() != OpenProjectDialog.DialogCode.Accepted:
            sys.exit(0)
        project_root = dlg.project_root
        project_name = Path(project_root).name
        video_root   = dlg.video_root

    cfg = _load_config()
    recent = cfg.get("recent_projects", [])
    if project_root in recent:
        recent.remove(project_root)
    recent.insert(0, project_root)
    cfg["recent_projects"] = recent[:8]
    _save_config(cfg)

    window = MainWindow(video_root=video_root, project_name=project_name)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
