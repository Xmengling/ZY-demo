#!/usr/bin/env bash
set -euo pipefail

PLIST_DST="$HOME/Library/LaunchAgents/com.zydemo.git-auto-push.plist"
LABEL="com.zydemo.git-auto-push"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || \
  launchctl unload "$PLIST_DST" 2>/dev/null || true

rm -f "$PLIST_DST"
echo "已卸载: $LABEL"
