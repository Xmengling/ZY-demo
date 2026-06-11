#!/usr/bin/env bash
# 安装 / 更新 ZY-demo 自动推送定时任务（macOS launchd）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_SRC="$REPO_ROOT/scripts/com.zydemo.git-auto-push.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.zydemo.git-auto-push.plist"
SCRIPT="$REPO_ROOT/scripts/git/auto-push.sh"
LABEL="com.zydemo.git-auto-push"

chmod +x "$SCRIPT"

if [[ ! -f "$PLIST_SRC" ]]; then
  echo "缺少 plist: $PLIST_SRC" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || \
  launchctl unload "$PLIST_DST" 2>/dev/null || true

launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null || \
  launchctl load "$PLIST_DST"

echo "已安装定时任务: $LABEL"
echo "  脚本: $SCRIPT"
echo "  日志: /tmp/zydemo-git-auto-push.log"
echo "  计划: 每天 20:00 自动 commit + push"
echo ""
echo "手动试跑: bash $SCRIPT"
echo "立即触发: launchctl kickstart -k gui/$(id -u)/$LABEL"
echo "卸载任务: launchctl bootout gui/$(id -u)/$LABEL"
