#!/usr/bin/env bash
# PostToolUse hook for Edit and Write. After a Python file is written, apply
# ruff's safe fixes and its formatter (config: ruff.toml at the repo root).
# If lint findings remain that ruff cannot fix, they are printed on stderr and
# the hook exits 2 so that Claude sees them and fixes them itself.

input=$(cat)
file=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty' <<<"$input")

case "$file" in *.py) ;; *) exit 0 ;; esac
case "$file" in */.venv/*) exit 0 ;; esac
[ -f "$file" ] || exit 0
command -v ruff >/dev/null 2>&1 || exit 0

ruff check --fix --quiet "$file" >/dev/null 2>&1
ruff format --quiet "$file" >/dev/null 2>&1

if ! remaining=$(ruff check --quiet --output-format=concise "$file" 2>&1); then
    echo "ruff found problems it could not fix automatically in $file:" >&2
    echo "$remaining" >&2
    exit 2
fi
exit 0
