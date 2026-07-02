%% prepare_masks.m
% 從影片截第一幀，用 U-Net（或 Otsu fallback）產生初始 mask
% 輸出：
%   input_frames/  → PNG 圖片
%   initial_masks/ → PNG 二值 mask（白=organoid, 黑=背景）
%
% 使用方式：
%   1. 把所有影片放進任意資料夾
%   2. 修改下面的 VIDEO_ROOT
%   3. 在 MATLAB 執行 prepare_masks

clear; clc;

%% ── 設定 ──────────────────────────────────────────────────────────────────
OUTPUT_ROOT  = fileparts(mfilename('fullpath'));  % annotation_tool/ 這個資料夾
FRAME_DIR    = fullfile(OUTPUT_ROOT, 'input_frames');   % 已有 raw_1.png ~ raw_82.png
MASK_DIR     = fullfile(OUTPUT_ROOT, 'initial_masks');
MIN_AREA_PX  = 5000;  % 最小 ROI 面積（pixel）

%% ── 掃描 PNG ──────────────────────────────────────────────────────────────
file_list = dir(fullfile(FRAME_DIR, 'raw_*.png'));
fprintf('找到 %d 張圖\n', length(file_list));
if isempty(file_list)
    error('找不到圖片，請確認 input_frames/ 資料夾');
end

%% ── 逐張處理 ──────────────────────────────────────────────────────────────
for i = 1:length(file_list)
    [~, stem, ~] = fileparts(file_list(i).name);
    outStem = stem;  % e.g. "raw_1"

    fprintf('[%d/%d] %s ... ', i, length(file_list), outStem);

    % 已處理過就跳過
    maskPath = fullfile(MASK_DIR, [outStem '_mask.png']);
    if exist(maskPath, 'file')
        fprintf('skip (已存在)\n');
        continue;
    end

    try
        % 讀圖
        framePath = fullfile(FRAME_DIR, file_list(i).name);
        frame = imread(framePath);

        % 產生 mask（U-Net 或 Otsu fallback）
        [mask, method] = predictMyocardiumUNet(frame, MIN_AREA_PX);

        % 存 mask PNG（二值：白=foreground）
        imwrite(uint8(mask) * 255, maskPath);

        fprintf('OK (%s, %d ROI pixels)\n', method, sum(mask(:)));

    catch ME
        fprintf('FAIL: %s\n', ME.message);
    end
end

fprintf('\n完成！\n');
fprintf('  圖片 → %s\n', FRAME_DIR);
fprintf('  Mask → %s\n', MASK_DIR);
fprintf('\n接下來：執行 python annotate.py 進行人工修正\n');
