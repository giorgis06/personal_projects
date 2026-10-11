#!/usr/bin/env bash
# PreToolUse hook for Bash. Blocks (exit 2) git commands that would change a
# protected branch directly:
#   - any force push
#   - a push that names a protected branch as its target
#   - commit or push while a protected branch is checked out
# Everything else passes. The message on stderr is shown to Claude.
#
# This guards against mistakes, not against a determined bypass: it reads the
# command text and the branch checked out when the command starts. The GitHub
# ruleset is what actually enforces the rule on the remote.

PROTECTED='master|ui/base-branch'

input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")
[ -z "$cmd" ] && exit 0

block() {
    echo "Blocked by .claude/hooks/guard-git.sh: $1" >&2
    exit 2
}

# One git invocation per shell segment, so "git status && git push -f" is caught.
while IFS= read -r segment; do
    grep -Eq '(^|[[:space:]])git([[:space:]]|$)' <<<"$segment" || continue

    if grep -Eq '[[:space:]]push([[:space:]]|$)' <<<"$segment"; then
        if grep -Eq '[[:space:]](--force|--force-with-lease|--force-if-includes|-[a-zA-Z]*f[a-zA-Z]*)([[:space:]=]|$)|[[:space:]]\+[^[:space:]]+' <<<"$segment"; then
            block "force pushes are not allowed in this repository."
        fi
        if grep -Eq "(^|[[:space:]:])($PROTECTED)([[:space:]]|\$)" <<<"$segment"; then
            block "do not push to a protected branch (master, ui/base-branch). Push your own branch and open a pull request."
        fi
    fi

    if grep -Eq '[[:space:]](commit|push)([[:space:]]|$)' <<<"$segment"; then
        branch=$(git -C "${cwd:-.}" branch --show-current 2>/dev/null)
        if grep -Eqx "$PROTECTED" <<<"$branch"; then
            block "'$branch' is protected. Create a branch first (git switch -c <name>), then commit and open a pull request."
        fi
    fi
done < <(sed -E 's/(&&|\|\||;|\|)/\n/g' <<<"$cmd")

exit 0
