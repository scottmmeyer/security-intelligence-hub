#!/usr/bin/env bash
set -u

repo_path="$(pwd)"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo UNKNOWN)"
head_sha="$(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)"
status_short="$(git status --short 2>/dev/null || true)"
upstream="$(git rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null || echo NONE)"

ahead=NA
behind=NA
if [ "$upstream" != "NONE" ]; then
  counts="$(git rev-list --left-right --count "${upstream}"...HEAD 2>/dev/null || true)"
  if [ -n "$counts" ]; then
    behind="$(printf '%s' "$counts" | awk '{print $1}')"
    ahead="$(printf '%s' "$counts" | awk '{print $2}')"
  fi
fi

echo "REPO_PATH=${repo_path}"
echo "BRANCH=${branch}"
echo "HEAD=${head_sha}"
echo "GIT_STATUS_SHORT="
printf '%s\n' "$status_short"
echo "UPSTREAM=${upstream}"
echo "AHEAD=${ahead}"
echo "BEHIND=${behind}"
