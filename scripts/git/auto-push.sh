#!/usr/bin/env bash
# 自动提交并推送 ZY-demo 到远程（供 launchd 定时调用）
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_FILE="${ZYDEMO_GIT_PUSH_LOG:-/tmp/zydemo-git-auto-push.log}"
BRANCH="${ZYDEMO_GIT_BRANCH:-main}"
REMOTE="${ZYDEMO_GIT_REMOTE:-origin}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

ensure_ssh() {
  if [[ -f "$HOME/.ssh/id_ed25519" ]]; then
    ssh-add --apple-use-keychain "$HOME/.ssh/id_ed25519" >/dev/null 2>&1 || true
  fi
}

has_sensitive_staged() {
  git diff --cached --name-only | while IFS= read -r path; do
    case "$path" in
      .env|.env.*|*.pem|*.key|*.p12|*.pfx)
        return 0
        ;;
    esac
  done
  return 1
}

stage_changes() {
  git add -u

  git add -A -- . \
    ':!.cursor/skills/jingfang-card-organizer/tmp' \
    ':!.npm-cache' \
    ':!ai-medical-consultant/backend/.venv312' \
    ':!ai-medical-consultant/backend/data/knowledge_uploads' \
    ':!ai-medical-consultant/frontend/.npm-cache' \
    ':!ai-medical-consultant/frontend/.tools' \
    ':!docs/exports/formula_cards/*.pdf' \
    2>/dev/null || true
}

cd "$REPO_ROOT"

if [[ ! -d .git ]]; then
  log "ERROR: not a git repo: $REPO_ROOT"
  exit 1
fi

ensure_ssh

current_branch="$(git branch --show-current)"
if [[ "$current_branch" != "$BRANCH" ]]; then
  log "SKIP: current branch is $current_branch, expected $BRANCH"
  exit 0
fi

if [[ -n "$(git status --porcelain)" ]]; then
  stage_changes

  if [[ -z "$(git diff --cached --name-only)" ]]; then
    log "SKIP: only excluded/untracked files changed"
    exit 0
  fi

  if has_sensitive_staged; then
    log "ERROR: sensitive files in staging area, abort commit"
    git reset HEAD >/dev/null 2>&1 || true
    exit 1
  fi

  stamp="$(date '+%Y-%m-%d %H:%M')"
  git commit -m "chore: auto sync ${stamp}"
  log "COMMIT: $(git rev-parse --short HEAD)"
else
  log "CLEAN: no local changes"
fi

if ! git pull --rebase "$REMOTE" "$BRANCH"; then
  log "ERROR: git pull --rebase failed (possible conflict)"
  exit 1
fi

if git push "$REMOTE" "$BRANCH"; then
  log "PUSH: ok -> ${REMOTE}/${BRANCH} ($(git rev-parse --short HEAD))"
else
  log "ERROR: git push failed"
  exit 1
fi
