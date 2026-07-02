import sys
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox,
    QHeaderView, QProgressBar, QAbstractItemView,
    QStyledItemDelegate, QStyleOptionButton, QStyle, QApplication,
)
from PyQt6.QtCore import Qt, QRect, QModelIndex
from PyQt6.QtGui import QColor, QPalette

PKL_DIR   = "_pkl_for_review"
DONE_COLOR    = ("#d6f0d6", "#2a6a2a")
PENDING_COLOR = ("#f0ebe0", "#8a8070")
ERROR_COLOR   = ("#fde0de", "#8a2a2a")


class _CentreCheckDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.row() == index.model().rowCount() - 1:
            super().paint(painter, option, index)
            return
        value = index.data(Qt.ItemDataRole.CheckStateRole)
        if value is None:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionButton()
        cb_size = QApplication.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, opt, None).size()
        x = option.rect.x() + (option.rect.width()  - cb_size.width())  // 2
        y = option.rect.y() + (option.rect.height() - cb_size.height()) // 2
        opt.rect = QRect(x, y, cb_size.width(), cb_size.height())
        opt.state = QStyle.StateFlag.State_Enabled
        if value == Qt.CheckState.Checked:
            opt.state |= QStyle.StateFlag.State_On
        else:
            opt.state |= QStyle.StateFlag.State_Off
        QApplication.style().drawControl(QStyle.ControlElement.CE_CheckBox, opt, painter)

    def editorEvent(self, event, model, option, index):
        if index.row() == model.rowCount() - 1:
            return False
        if event.type() in (
            event.Type.MouseButtonRelease,
            event.Type.MouseButtonDblClick,
        ):
            current = index.data(Qt.ItemDataRole.CheckStateRole)
            new_state = (Qt.CheckState.Unchecked
                         if current == Qt.CheckState.Checked
                         else Qt.CheckState.Checked)
            model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
            return True
        return False


def _scan_rows(video_root: str, project_name: str) -> list[dict]:
    """
    Scan video_root for videos and read their status from pkl sidecars.
    Returns list of dicts: exp, day, filename, path, computed, reviewed, result
    """
    # add project root to sys.path so we can import cardio_py
    proj_root = str(Path(__file__).parent.parent.parent)
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)

    try:
        from cardio_py.core.io import scan_video_folder
        videos = scan_video_folder(video_root)
    except Exception:
        return []

    pkl_dir = Path(video_root) / project_name / PKL_DIR
    rows = []
    for v in videos:
        vp   = Path(v['path'])
        # matches _get_pkl_path: parent.name (Day folder) + stem
        stem = f"{vp.parent.name}_{vp.stem}"
        pkl  = pkl_dir / f"{stem}.pkl"
        sidecar = pkl.with_suffix('.json')

        computed     = pkl.exists()
        reviewed     = False
        last_updated = "—"

        if computed:
            if sidecar.exists():
                try:
                    meta = json.loads(sidecar.read_text())
                    reviewed = meta.get('status', '') == 'Reviewed'
                except Exception:
                    pass
            try:
                mtime = pkl.stat().st_mtime
                last_updated = datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")
            except Exception:
                last_updated = "—"

        rows.append({
            'exp':          v['exp_name'],
            'day':          v['day'],
            'filename':     v['filename'],
            'path':         v['path'],
            'computed':     computed,
            'reviewed':     reviewed,
            'last_updated': last_updated,
        })
    return rows


class DashboardTab(QWidget):
    def __init__(self, open_review_fn=None, video_root: str = "", project_name: str = "", parent=None):
        super().__init__(parent)
        self._open_review  = open_review_fn
        self._video_root   = video_root
        self._project_name = project_name
        self._rows: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 14)
        root.setSpacing(14)

        # ── Title ──
        title_row = QHBoxLayout()
        title = QLabel("MyoOptix")
        title.setProperty("heading", True)
        sub = QLabel("Cardiac Organoid Analysis")
        sub.setProperty("subtitle", True)
        sub.setAlignment(Qt.AlignmentFlag.AlignBottom)
        title_row.addWidget(title)
        title_row.addSpacing(10)
        title_row.addWidget(sub)
        title_row.addStretch()
        switch_btn = QPushButton("⇄  Switch Project")
        switch_btn.setFixedHeight(30)
        switch_btn.clicked.connect(self._switch_project)
        title_row.addWidget(switch_btn)
        root.addLayout(title_row)

        proj_bar = QLabel(f"Project:  {self._project_name}   |   Root:  {self._video_root}")
        proj_bar.setStyleSheet(
            "background: #ede8de; border: 1px solid #d6cfc2; border-radius: 4px;"
            "padding: 4px 10px; font-size: 11px; color: #6b6456;"
        )
        root.addWidget(proj_bar)

        # ── Stats ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self._stat_labels = {}
        for label, color in [
            ("Total",    "#3b3a32"),
            ("Pending",  "#b07a10"),
            ("Computed", "#2a5a8a"),
            ("Reviewed", "#2a6a2a"),
        ]:
            card, val_lbl = self._stat_card(label, "0", color)
            self._stat_labels[label] = val_lbl
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.refresh_btn = QPushButton("⟳  Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        self.compute_btn = QPushButton("▶  Batch Compute")
        self.compute_btn.setProperty("primary", True)
        self.compute_btn.style().unpolish(self.compute_btn)
        self.compute_btn.style().polish(self.compute_btn)
        self.compute_btn.clicked.connect(self._batch_compute)
        self.review_btn  = QPushButton("Review")
        self.review_btn.clicked.connect(self._open_review_selected)
        self.report_btn  = QPushButton("⬇  Generate Report")
        self.report_btn.clicked.connect(self._generate_report)

        for b in (self.refresh_btn, self.compute_btn, self.review_btn, self.report_btn):
            b.setFixedHeight(32)
            btn_row.addWidget(b)
        root.addLayout(btn_row)

        # ── Progress ──
        self.progress = QProgressBar()
        self.progress.setFixedHeight(5)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["", "Exp", "Time", "File", "Computed", "Reviewed", "Last Updated"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 130)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setMouseTracking(True)
        self._hover_row = -1
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.leaveEvent = self._on_table_leave
        self._chk_delegate = _CentreCheckDelegate(self.table)
        self.table.setItemDelegateForColumn(0, self._chk_delegate)
        self.table.cellClicked.connect(self._on_cell_clicked)
        root.addWidget(self.table)

    def _on_cell_entered(self, row, col):
        if row == self._hover_row:
            return
        old = self._hover_row
        self._hover_row = row
        self._repaint_row(old)
        self._repaint_row(row)

    def _on_table_leave(self, event):
        old = self._hover_row
        self._hover_row = -1
        self._repaint_row(old)

    def _repaint_row(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        is_hover = (row == self._hover_row)
        is_plus  = (row == self.table.rowCount() - 1)
        if is_plus:
            return
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item is None:
                continue
            # preserve special colors for Computed/Reviewed cols
            if col in (4, 5):
                text = item.text()
                if text == "Done":
                    bg = QColor("#c0e8c0") if is_hover else QColor(DONE_COLOR[0])
                else:
                    bg = QColor("#e0d8c8") if is_hover else QColor(PENDING_COLOR[0])
                item.setBackground(bg)
            else:
                bg = QColor("#e8e2d6") if is_hover else QColor("#faf7f2")
                item.setBackground(bg)

    def refresh(self):
        self._rows = _scan_rows(self._video_root, self._project_name)
        self._populate_table()
        self._update_stats()

    def _update_stats(self):
        total    = len(self._rows)
        computed = sum(1 for r in self._rows if r['computed'])
        reviewed = sum(1 for r in self._rows if r['reviewed'])
        pending  = total - computed
        self._stat_labels["Total"].setText(str(total))
        self._stat_labels["Pending"].setText(str(pending))
        self._stat_labels["Computed"].setText(str(computed))
        self._stat_labels["Reviewed"].setText(str(reviewed))

    def _stat_card(self, label, value, color):
        card = QGroupBox()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)
        v = QLabel(value)
        v.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color}; background: transparent;")
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l = QLabel(label)
        l.setStyleSheet("font-size: 11px; color: #8a8070; background: transparent;")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(v)
        lay.addWidget(l)
        return card, v

    def _populate_table(self):
        self.table.setRowCount(0)
        for r, row in enumerate(self._rows):
            self.table.insertRow(r)
            # checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, row['path'])
            self.table.setItem(r, 0, chk)
            # Exp, Day, File
            for c, val in enumerate([row['exp'], row['day'], row['filename']], start=1):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
            # Computed
            comp_text = "Done" if row['computed'] else "Pending"
            comp_bg, comp_fg = DONE_COLOR if row['computed'] else PENDING_COLOR
            ci = QTableWidgetItem(comp_text)
            ci.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ci.setBackground(QColor(comp_bg))
            ci.setForeground(QColor(comp_fg))
            self.table.setItem(r, 4, ci)
            # Reviewed
            rev_text = "Done" if row['reviewed'] else "Pending"
            rev_bg, rev_fg = DONE_COLOR if row['reviewed'] else PENDING_COLOR
            ri = QTableWidgetItem(rev_text)
            ri.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            ri.setBackground(QColor(rev_bg))
            ri.setForeground(QColor(rev_fg))
            self.table.setItem(r, 5, ri)
            # Last Updated
            res_item = QTableWidgetItem(row['last_updated'])
            res_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            res_item.setForeground(QColor("#6b6456"))
            self.table.setItem(r, 6, res_item)

        # + row
        plus_row = self.table.rowCount()
        self.table.insertRow(plus_row)
        plus_item = QTableWidgetItem("＋  Add Videos")
        plus_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        plus_item.setForeground(QColor("#7c9c6e"))
        plus_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(plus_row, 0, plus_item)
        self.table.setSpan(plus_row, 0, 1, 7)

    def get_checked_paths(self) -> list[str]:
        paths = []
        for r in range(self.table.rowCount() - 1):
            item = self.table.item(r, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                paths.append(item.data(Qt.ItemDataRole.UserRole))
        return paths

    def _on_cell_clicked(self, row, col):
        if row == self.table.rowCount() - 1:
            self._add_videos()

    def _add_videos(self):
        from .dialog_import import ImportDialog
        dlg = ImportDialog(project_root=self._video_root, parent=self)
        if dlg.exec() == ImportDialog.DialogCode.Accepted:
            self.refresh()

    def _batch_compute(self):
        from .dialog_compute import ComputeDialog
        paths = self.get_checked_paths()
        if not paths:
            # if nothing checked, use all
            paths = [r['path'] for r in self._rows]
        if not paths:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "No videos", "No videos to compute.")
            return
        project_root = str(Path(self._video_root) / self._project_name)
        settings_path = Path(project_root) / "compute_settings.json"
        default_scale = 10000 / 1530
        if settings_path.exists():
            try:
                s = json.loads(settings_path.read_text())
                default_scale = s.get("scale", default_scale)
            except Exception:
                pass
        dlg = ComputeDialog(
            video_paths=paths,
            project_root=project_root,
            scale=default_scale,
            k_mult=1.0,
            min_dist=0.2,
            parent=self,
        )
        dlg.exec()
        self.refresh()

    def _open_review_selected(self):
        from .dialog_review import ReviewDialog
        from PyQt6.QtWidgets import QMessageBox
        paths = self.get_checked_paths()
        if not paths:
            QMessageBox.information(self, "No selection",
                "Please check the box next to video(s) you want to review.")
            return
        project_root = Path(self._video_root) / self._project_name
        for vp in paths:
            p = Path(vp)
            pkl_path = str(project_root / "_pkl_for_review" /
                           f"{p.parent.name}_{p.stem}.pkl")
            if not Path(pkl_path).exists():
                QMessageBox.warning(self, "Not computed",
                    f"{p.name} has not been computed yet. Skipping.")
                continue
            dlg = ReviewDialog(pkl_path=pkl_path, parent=self)
            self._review_dlg = dlg  # prevent GC crash
            dlg.exec()
        self.refresh()

    def _generate_report(self):
        from PyQt6.QtWidgets import QMessageBox
        import sys, os
        import pandas as pd

        proj_root_str = str(Path(self._video_root) / self._project_name)
        xlsx_dir = Path(proj_root_str) / "final_excel_exports"

        # determine which videos to merge — only Reviewed ones (matching MATLAB behaviour)
        pkl_dir = Path(proj_root_str) / PKL_DIR
        checked_paths = self.get_checked_paths()
        candidate_paths = checked_paths if checked_paths else [r['path'] for r in self._rows]

        xlsx_files = []
        skipped_not_reviewed = 0
        for vp in candidate_paths:
            p    = Path(vp)
            stem = f"{p.parent.name}_{p.stem}"
            # check Reviewed status via sidecar
            sidecar = pkl_dir / f"{stem}.json"
            is_reviewed = False
            if sidecar.exists():
                try:
                    meta = json.loads(sidecar.read_text())
                    is_reviewed = meta.get('status', '') == 'Reviewed'
                except Exception:
                    pass
            if not is_reviewed:
                skipped_not_reviewed += 1
                continue
            f = xlsx_dir / f"{stem}_analysis_results.xlsx"
            if f.exists():
                xlsx_files.append(f)

        if not xlsx_files:
            msg = "No Reviewed videos with exported Excel files found."
            if skipped_not_reviewed:
                msg += f"\n\n{skipped_not_reviewed} video(s) were skipped because they are not yet Reviewed.\nPlease complete Review and Export before generating a report."
            QMessageBox.information(self, "No results", msg)
            return

        scope_label = "checked" if checked_paths else "all"
        scope_msg = f"{len(xlsx_files)} {scope_label} Reviewed video(s)"
        if skipped_not_reviewed:
            scope_msg += f"  ({skipped_not_reviewed} non-Reviewed skipped)"

        ans = QMessageBox.question(self, "Generate Report",
            f"Merge {scope_msg} into a report?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if ans != QMessageBox.StandardButton.Yes:
            return

        metric_map = {
            'BPM':                      'BPM',
            'IBI_avg':                  'Interbeat Interval (IBI)',
            'HRV':                      'HRV',
            'ST_s':                     'Systolic Time (ST)',
            'DT_s':                     'Diastolic Time (DT)',
            'Interbeatsegment_s':       'Interbeat Segment',
            'Contractility_Mag_um_s':   'Contractility',
            'Contractility_Std_um_s':   'Contractility Std',
        }

        try:
            # build video list (stem = "{Day}_{VideoName}")
            videos = []
            for f in xlsx_files:
                stem  = f.name.replace("_analysis_results.xlsx", "")
                parts = stem.split("_", 1)
                videos.append({
                    'exp_name':   self._project_name,
                    'time':       parts[0] if len(parts) > 1 else stem,
                    'video_name': parts[1] if len(parts) > 1 else stem,
                    'excel_path': str(f),
                })

            universal_rows = []
            roi_avgs       = []

            for v in videos:
                sheets = pd.read_excel(v['excel_path'], sheet_name=None, engine='openpyxl')
                for sheet_name, df in sheets.items():
                    sample_id = f"{v['time']}_{v['video_name']}_{sheet_name}"
                    avg_row   = {'Group': v['exp_name'], 'Time': v['time'], 'SampleID': sample_id}
                    for col, label in metric_map.items():
                        vals = df[col].dropna() if col in df.columns else pd.Series(dtype=float)
                        val  = round(float(vals.mean()), 6) if len(vals) > 0 else float('nan')
                        avg_row[label] = val
                        universal_rows.append({
                            'Group':      v['exp_name'],
                            'SampleID':   sample_id,
                            'Metric':     label,
                            'Value':      val,
                            'SourceFile': f"{os.path.basename(v['excel_path'])} - {sheet_name}",
                        })
                    roi_avgs.append(avg_row)

            metric_labels = list(metric_map.values())
            all_groups    = sorted({r['Group'] for r in roi_avgs})
            all_times     = sorted({r['Time']  for r in roi_avgs})
            wide_rows     = []
            for grp in all_groups:
                wide_rows.append([f'GROUP: {grp}'])
                for t in all_times:
                    day_rois = [r for r in roi_avgs if r['Group'] == grp and r['Time'] == t]
                    if not day_rois:
                        continue
                    wide_rows.append([t])
                    wide_rows.append([None] + [r['SampleID'] for r in day_rois])
                    for m in metric_labels:
                        wide_rows.append([m] + [round(r.get(m, float('nan')), 6) for r in day_rois])
                    wide_rows.append([])

            max_cols = max(len(r) for r in wide_rows)
            df_wide  = pd.DataFrame([r + [None] * (max_cols - len(r)) for r in wide_rows])
            df_univ  = pd.DataFrame(universal_rows)[['Group', 'SampleID', 'Metric', 'Value', 'SourceFile']]
            # add Time column to universal results
            time_map = {f"{v['time']}_{v['video_name']}": v['time'] for v in videos}
            df_univ.insert(1, 'Time',
                df_univ['SampleID'].apply(lambda s: next(
                    (t for k, t in time_map.items() if s.startswith(k)), ''
                ))
            )

            report_dir = Path(proj_root_str) / "_Merged_Reports"
            report_dir.mkdir(exist_ok=True)
            out_path = str(report_dir / f"{self._project_name}_Report.xlsx")
            with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
                df_univ.to_excel(writer, sheet_name='Universal Results', index=False)
                df_wide.to_excel(writer, sheet_name='Grouped by Time',   index=False)

            QMessageBox.information(self, "Done",
                f"Report saved ({len(videos)} video(s)):\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _switch_project(self):
        from .dialog_project import ProjectDialog
        dlg = ProjectDialog(video_root=self._video_root, parent=self)
        if dlg.exec() == ProjectDialog.DialogCode.Accepted:
            window = self.window()
            window.close()
            from .main_window import MainWindow
            new_win = MainWindow(
                video_root=self._video_root,
                project_name=dlg.project_name,
            )
            new_win.show()
