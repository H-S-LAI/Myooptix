#!/usr/bin/env bash
# SessionStart hook — 開場回報這台機器與 origin 的同步狀態。
#
# 跨平台限制（macOS 與 Windows Git Bash 都必須能跑）：
#   - 不使用 jq（Windows 通常沒有）
#   - 不做 date 算術（BSD date 與 GNU date 旗標不同），改用 git 的 %cr 相對時間
#   - 不使用 $CLAUDE_PROJECT_DIR（實測某些環境為空值）
#   - 任何步驟失敗都靜默略過並 exit 0，絕不讓 hook 噴錯干擾 session
#
# 輸出為純文字，SessionStart 會把 stdout 併入 context。

cd "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || exit 0

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0

# 抓遠端狀態。離線時 fetch 會失敗，不影響後續（只是數字較舊）
git fetch --quiet 2>/dev/null

BEHIND=$(git rev-list --count "HEAD..@{u}" 2>/dev/null || echo "?")
AHEAD=$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo "?")
DIRTY=$(git status --porcelain 2>/dev/null | grep -c "^ *[MARCD]" || echo 0)

echo "【MyoOptix 跨機同步狀態】"
echo "分支 $BRANCH｜落後 origin $BEHIND｜領先 $AHEAD｜未提交 $DIRTY"

if [ -f DEVLOG.md ]; then
  LAST_ENTRY=$(grep "^## 20" DEVLOG.md 2>/dev/null | tail -1)
  [ -n "$LAST_ENTRY" ] && echo "DEVLOG 最後一則：${LAST_ENTRY#\#\# }"
  # 只有已提交的內容才會同步到另一台，所以分開報「最後提交」與「有未提交」
  echo "DEVLOG 最後提交：$(git log -1 --format='%cr' -- DEVLOG.md 2>/dev/null)"
  [ -n "$(git status --porcelain DEVLOG.md 2>/dev/null)" ] && \
    echo "→ DEVLOG 有未提交內容，另一台看不到。收尾時 commit + push"
fi

# 提醒只在真的需要時出現，避免每次開場都在喊狼來了
[ "$BEHIND" != "0" ] && [ "$BEHIND" != "?" ] && \
  echo "→ 落後 origin，開始改東西之前先 git pull（本 repo 有 .gitattributes，pull 前請先 commit 或 stash）"
[ "$AHEAD" != "0" ] && [ "$AHEAD" != "?" ] && \
  echo "→ 有 $AHEAD 個 commit 未 push，另一台機器看不到。收尾時記得 push"

exit 0
