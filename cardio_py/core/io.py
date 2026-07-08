"""
I/O utilities
=============
Video reading and Excel export, ported from ProjectDashboard / reviewMyocardium.
"""

import os
import numpy as np
import pandas as pd
import cv2
from pathlib import Path


# ── Video ──────────────────────────────────────────────────────────────────

def read_first_frame(video_path: str) -> tuple[np.ndarray, float]:
    """
    Read the first frame and frame rate from a video file.

    Returns
    -------
    frame_rgb  : (H, W, 3) uint8 RGB image
    frame_rate : fps
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    ret, frame_bgr = cap.read()
    cap.release()
    if not ret:
        raise IOError(f"Cannot read first frame from: {video_path}")
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), frame_rate


def scan_video_folder(root: str, extensions: tuple = ('.mov', '.mp4', '.avi')) -> list[dict]:
    """
    Recursively scan a folder for video files.
    Returns list of dicts with keys: path, filename, exp_name, day.

    Folder structure assumed: <root>/<exp_name>/<day>/<filename>
    """
    videos = []
    root = Path(root)
    for ext in extensions:
        for p in sorted(root.rglob(f'*{ext}')):
            if p.name.startswith('._'):
                continue
            parts = p.relative_to(root).parts
            if len(parts) >= 3:
                exp_name = parts[0]
                day      = parts[1]
            elif len(parts) == 2:
                exp_name = parts[0]
                day      = '—'
            else:
                exp_name = '—'
                day      = '—'
            videos.append({
                'path':     str(p),
                'filename': p.name,
                'exp_name': exp_name,
                'day':      day,
            })
    return videos


# ── Excel export ───────────────────────────────────────────────────────────

def export_analysis_excel(
    output_path: str,
    roi_results: list[dict],
    time: np.ndarray,
) -> None:
    """
    Export per-ROI analysis results to Excel.
    Matches the format produced by reviewMyocardium_v1.m exportCallback.

    Each ROI gets two sheets:
      - {prefix}_{i}_{axis}_Axis          : per-beat analysis (analysis_results)
      - {prefix}_{i}_{axis}_Axis_raw      : raw velocity + force traces (raw_data)

    Parameters
    ----------
    output_path : path to output .xlsx file
    roi_results : list of dicts, one per ROI, with keys:
        roi_index, dominant_axis, signal (velocity µm/s), global_trace,
        mdp (BeatMetrics), force (dict from compute_contractility)
    time        : time vector (s)
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    base = output_path.removesuffix('.xlsx')
    analysis_path = base + '_analysis_results.xlsx'
    raw_path      = base + '_raw_data.xlsx'

    with pd.ExcelWriter(analysis_path, engine='openpyxl') as w_an, \
         pd.ExcelWriter(raw_path,      engine='openpyxl') as w_raw:

        for i_seq, r in enumerate(roi_results, start=1):
            i     = i_seq          # use sequential index, ignoring stored roi_index
            axis  = r['dominant_axis']
            mdp   = r['mdp']
            force = r['force']
            sig   = r['signal']
            gt    = r['global_trace']
            prefix = r.get('roi_prefix', 'ROI')
            safe_axis = axis.replace('(', '').replace(')', '').replace('°', 'deg').replace('+', 'p').replace('-', 'n')
            sheet = f'{prefix}_{i}_{safe_axis}'

            # ── Raw data sheet ──────────────────────────────
            n = min(len(time), len(sig), len(gt))
            df_raw = pd.DataFrame({
                'Time_s':              time[:n],
                'Velocity_um_s':       sig[:n],
                'Global_Force_um_s':   gt[:n],
            })
            df_raw.to_excel(w_raw, sheet_name=sheet, index=False)

            # ── Analysis results sheet ──────────────────────
            if mdp.HR == 0:
                continue

            n_peaks = mdp.HR
            ibi_arr = np.diff(mdp.peak_locs)
            fv = force['force_vals']
            c_std = float(np.nanstd(fv)) if len(fv) > 1 else float('nan')

            morph = r.get('morphology', {})
            diam_um = morph.get('equivalent_diameter_um', float('nan'))

            rows = []
            for k in range(n_peaks):
                st_val  = float(mdp.ST[k])        if k < len(mdp.ST)        else float('nan')
                dt_val  = float(mdp.DT[k])        if k < len(mdp.DT)        else float('nan')
                ib_val  = float(mdp.Interbeat[k]) if k < len(mdp.Interbeat) else float('nan')
                ibi_val = float(ibi_arr[k])        if k < len(ibi_arr)       else float('nan')
                f_val   = float(fv[k]) if k < len(fv) else float('nan')

                rows.append({
                    'PeakTime_s':                float(mdp.peak_locs[k]),
                    'PeakHeight':                float(mdp.peaks[k]),
                    'IBI_s':                     ibi_val,
                    'IBI_avg':                   float(mdp.IBI_avg),
                    'HRV':                       float(np.nanstd(ibi_arr)) if len(ibi_arr) > 0 else float('nan'),
                    'BPM':                       60.0 / float(mdp.IBI_avg) if mdp.IBI_avg > 0 else float('nan'),
                    'ST_s':                      st_val,
                    'DT_s':                      dt_val,
                    'Interbeatsegment_s':         ib_val,
                    'Contractility_Mag_um_s':    f_val,
                    'Contractility_Std_um_s':    c_std,
                    'Equivalent_Diameter_um':    diam_um,
                })

            pd.DataFrame(rows).to_excel(w_an, sheet_name=sheet, index=False)


def export_summary_table(
    output_path: str,
    all_videos: list[dict],
) -> None:
    """
    Merge all per-video analysis results into a single summary Excel.
    Matches the format of ProjectBatchMerger_v1.m output.

    Parameters
    ----------
    output_path : path to merged .xlsx file
    all_videos  : list of dicts with keys:
        exp_name, day, file_id, video_name, excel_path
    """
    metrics = ['BPM', 'IBI_avg', 'HRV', 'ST_s', 'DT_s', 'Interbeatsegment_s', 'Contractility_Mag_um_s', 'Contractility_Std_um_s']
    rows = []

    for v in all_videos:
        excel_path = v.get('excel_path', '')
        if not os.path.exists(excel_path):
            continue
        try:
            sheets = pd.read_excel(excel_path, sheet_name=None)
        except Exception:
            continue

        for sheet_name, df in sheets.items():
            for m in metrics:
                if m in df.columns:
                    val = float(df[m].dropna().mean()) if not df[m].dropna().empty else float('nan')
                else:
                    val = float('nan')
                rows.append({
                    'Group':     v.get('exp_name', ''),
                    'Day':       v.get('day', ''),
                    'SampleID':  f"{v.get('day','')}_{v.get('video_name','')}_{sheet_name}",
                    'Metric':    m,
                    'Value':     val,
                    'SourceFile': os.path.basename(excel_path) + ' - ' + sheet_name,
                })

    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_out.to_excel(writer, sheet_name='Universal Results', index=False)
