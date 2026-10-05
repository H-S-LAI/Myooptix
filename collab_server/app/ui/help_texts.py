"""Per-screen help content (中英並陳), shown by the ? button on each dialog."""

_CSS = """
<style>
  body  { font-size: 13px; color: #3b3a32; }
  h3    { font-size: 14px; color: #3b3a32; margin: 14px 0 4px; }
  p     { margin: 4px 0 8px; line-height: 1.55; }
  .en   { color: #6b6456; }
  table { border-collapse: collapse; margin: 4px 0 10px; }
  td    { padding: 3px 10px 3px 0; vertical-align: top; line-height: 1.5; }
  td.k  { color: #3b5a8a; font-weight: bold; white-space: nowrap; }
  .note { background: #f4f1e8; padding: 8px 10px; border-left: 3px solid #7c9c6e; }
</style>
"""

HELP = {

"login": _CSS + """
<h3>登入 Sign in</h3>
<p>用申請核准後收到的信箱與密碼登入。登入狀態會保留，下次開啟通常不需重新輸入。<br>
<span class="en">Sign in with the email and password from your approval email. Your session is remembered.</span></p>

<h3>沒有帳號 No account</h3>
<p>點下方 <b>Request access</b> 提出申請，管理者核准後你會收到通知信。<br>
<span class="en">Click <b>Request access</b> below. You will be notified once an administrator approves it.</span></p>

<h3>登入失敗 If sign-in fails</h3>
<table>
<tr><td class="k">Invalid email or password</td><td>帳號或密碼錯誤，或帳號尚未核准<br><span class="en">Wrong credentials, or the account is not approved yet</span></td></tr>
<tr><td class="k">Cannot reach server</td><td>網路不通，或你的電腦憑證過舊。本版已內建備援憑證，若仍失敗請聯絡管理者<br><span class="en">No network, or an outdated certificate store on your computer. Contact the administrator if it persists</span></td></tr>
</table>
""",

"register": _CSS + """
<h3>申請帳號 Request access</h3>
<p>請填寫真實姓名與單位，管理者會依此審核。送出後需等待核准，核准結果會寄到你填的信箱。<br>
<span class="en">Use your real name and institution — an administrator reviews each request. You will receive an email once it is approved.</span></p>

<h3>密碼 Password</h3>
<p>密碼由你自己設定，請妥善保存。送出後無法自行修改，需要時請聯絡管理者。<br>
<span class="en">You choose your own password. It cannot be changed in the app; contact the administrator if needed.</span></p>
""",

"quick": _CSS + """
<h3>分析流程 Workflow</h3>
<p>1. 選擇影片 → 2. 設定影像尺度（Scale）→ 3. 選擇切割方式 → 4. 執行 → 5. 在 Review 畫面檢查並匯出<br>
<span class="en">1. Choose a video → 2. Set the scale → 3. Choose segmentation → 4. Run → 5. Check and export in Review</span></p>

<h3>影像尺度 Scale（µm / pixel）</h3>
<p>表示影像中<b>一個像素代表多少微米</b>。這個值決定所有長度單位的換算。<br>
<span class="en">How many micrometres one pixel represents. It converts every length-based result.</span></p>

<p><b>怎麼量 How to measure</b></p>
<table>
<tr><td class="k">1</td><td>在<b>與實驗完全相同</b>的物鏡、相機、解析度設定下，拍一張載玻片微尺（stage micrometer）或已知尺寸物體的照片<br>
<span class="en">Image a stage micrometer, or any object of known size, with exactly the same objective, camera and resolution as your experiment</span></td></tr>
<tr><td class="k">2</td><td>量出已知長度在影像中佔幾個像素<br><span class="en">Measure how many pixels that known length spans</span></td></tr>
<tr><td class="k">3</td><td>Scale = 已知長度 (µm) ÷ 像素數。例如 1000 µm 佔 343 像素 → 2.915 µm/px<br>
<span class="en">Scale = known length (µm) ÷ pixel count. e.g. 1000 µm over 343 px → 2.915 µm/px</span></td></tr>
</table>

<p><b>直接用預設值會怎樣 If you keep the preset</b></p>
<p>預設值<b>來自系統開發者的顯微鏡設定</b>。只要<b>物鏡倍率、相機、影像解析度或裁切範圍</b>有一項不同，這個值就不適用。<br>
<span class="en">The presets come from the developer's own microscope setup. A different objective, camera, resolution or crop makes them wrong.</span></p>
<table>
<tr><td class="k">會受影響</td><td>Contractility（µm/s）、Diameter（µm）、Area（µm²）<br>
尺度錯幾倍，這些數值就跟著錯幾倍<br>
<span class="en">Scale directly multiplies these — a 2× wrong scale gives 2× wrong values</span></td></tr>
<tr><td class="k">不受影響</td><td>BPM、IBI、HRV、ST、DT、Interbeat segment<br>
這些只與時間有關<br><span class="en">Purely time-based, unaffected by the scale</span></td></tr>
</table>
<p class="note">同一批要互相比較的影片，必須使用<b>同一個 Scale</b>。不同 Scale 算出的 Contractility 不能直接比較。<br>
<span class="en">Use one scale for every video you intend to compare. Contractility from different scales is not comparable.</span></p>

<h3>切割方式 Segmentation</h3>
<table>
<tr><td class="k">U-Net</td><td>深度學習模型，自動找出類器官，適合一般明視野影像<br><span class="en">Deep-learning model; the default for brightfield images</span></td></tr>
<tr><td class="k">Otsu</td><td>以亮度閾值切割，速度快，適合對比明顯、背景乾淨的影像<br><span class="en">Threshold-based; fast, for high-contrast images</span></td></tr>
</table>
""",

"review": _CSS + """
<h3>這個畫面在做什麼 What this screen is for</h3>
<p>逐一檢查每顆類器官的偵測結果，必要時調整參數或刪除不要的 ROI，確認無誤後匯出。<br>
<span class="en">Check each organoid, adjust parameters or delete unwanted ROIs, then export.</span></p>

<h3>三個波形圖 The three plots</h3>
<p>最上方縮圖顯示這顆 ROI 在影像中的位置。<br>
<span class="en">The thumbnail above shows where this ROI sits in the frame.</span></p>
<table>
<tr><td class="k">上</td><td>速度訊號<br><span class="en">Velocity signal</span></td></tr>
<tr><td class="k">中</td><td>速度訊號中偵測到的收縮事件（★ 峰值、CS、CE、RE）<br><span class="en">Beat events detected in the velocity signal (★ peak, CS, CE, RE)</span></td></tr>
<tr><td class="k">下</td><td>收縮強度曲線，★ 為每一拍取用的值<br><span class="en">Baseline-corrected contractility trace; stars are the per-beat values</span></td></tr>
</table>

<h3>收縮事件 Beat events</h3>
<table>
<tr><td class="k">CS</td><td>收縮開始 — 速度上升超過該拍峰值的 5%<br><span class="en">Contraction Start — velocity rises past 5% of the peak</span></td></tr>
<tr><td class="k">CE</td><td>收縮結束 — 峰值之後速度下降通過零<br><span class="en">Contraction End — velocity crosses zero after the peak</span></td></tr>
<tr><td class="k">RE</td><td>舒張結束 — 速度自低谷回升至該低谷的 5%<br><span class="en">Relaxation End — velocity returns to 5% of the trough</span></td></tr>
</table>

<h3>輸出的變量 Exported metrics</h3>
<table>
<tr><td class="k">BPM</td><td>每分鐘收縮次數 = 60 ÷ 平均 IBI<br><span class="en">Beats per minute = 60 / mean IBI</span></td></tr>
<tr><td class="k">IBI (s)</td><td>連續兩次 CS 之間的時間<br><span class="en">Inter-beat interval: time between consecutive CS events</span></td></tr>
<tr><td class="k">HRV (s)</td><td>同一支影片中所有 IBI 的標準差。數值越大代表節律越不規律<br>
<span class="en">Standard deviation of all IBIs in the video; larger = more irregular rhythm</span></td></tr>
<tr><td class="k">ST (s)</td><td>收縮時間 = CE − CS<br><span class="en">Systolic time</span></td></tr>
<tr><td class="k">DT (s)</td><td>舒張時間 = RE − CE<br><span class="en">Diastolic time</span></td></tr>
<tr><td class="k">Interbeat<br>segment (s)</td><td>本拍 RE 到下一拍 CS 的間隔，即兩拍之間的靜止期<br>
<span class="en">From this beat's RE to the next CS — the quiescent gap between beats</span></td></tr>
<tr><td class="k">Contractility<br>(µm/s)</td><td>每一拍在峰值附近、扣除基線後的平均移動速度。<b>是速度，不是力</b>，數值受影像尺度影響<br>
<span class="en">Mean baseline-corrected motion speed per beat. A velocity, not a force; depends on the scale</span></td></tr>
<tr><td class="k">Contractility<br>Std (µm/s)</td><td>同一顆類器官各拍 Contractility 的標準差，反映每拍之間的變異<br>
<span class="en">Standard deviation of per-beat contractility — beat-to-beat variability</span></td></tr>
<tr><td class="k">Diameter<br>(µm)</td><td>與 ROI 面積相同的圓形直徑（等效直徑）<br><span class="en">Equivalent circular diameter of the ROI area</span></td></tr>
</table>

<h3>兩個可調參數 Adjustable parameters</h3>
<table>
<tr><td class="k">K multiplier</td><td>峰值偵測的高度門檻 = K × 訊號標準差。調高會略過較弱的收縮，調低會納入更多小波動<br>
<span class="en">Peak height threshold = K × signal SD. Higher ignores weak beats; lower picks up more noise</span></td></tr>
<tr><td class="k">Min distance</td><td>兩個峰值之間的最短間隔（秒）。跳得很快的樣本需要調小，否則會漏拍<br>
<span class="en">Minimum spacing between peaks. Lower it for fast-beating samples, or beats will be missed</span></td></tr>
</table>
<p>調整後圖表會即時重算，確認偵測正確再匯出。<br>
<span class="en">Plots recompute as you adjust; export once the detection looks right.</span></p>

<h3>刪除 ROI Delete ROI</h3>
<p>切到邊緣、重疊、或根本沒有跳動的 ROI 可以刪除，不會納入匯出結果。<br>
<span class="en">Remove ROIs cut off by the frame edge, overlapping, or not beating. They are excluded from the export.</span></p>
""",
}
