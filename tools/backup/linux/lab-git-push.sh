#!/usr/bin/env bash
# lab-git-push.sh — Just commit and push any pending changes
# Useful as a lightweight hourly job
set -euo pipefail

REPO_DIR="$HOME/Lab"
HOSTNAME=$(hostname)
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

cd "$REPO_DIR"
git pull --rebase --quiet 2>/dev/null || true
git add -A 2>/dev/null || true

if git diff --cached --quiet; then
    exit 0
fi

git commit -m "node:$HOSTNAME sync $DATE $TIME" --quiet
git push --quiet 2>/dev/null || echo "Push failed"
