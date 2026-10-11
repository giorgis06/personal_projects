#!/usr/bin/env bash
# PreToolUse hook for Edit and Write. The C++ solver in fem_solver/ is written
# by hand by the repository owner, so an edit there must be approved by them:
#   - vendored headers (doctest.h, gmsh.h) are refused outright
#   - any other solver file outside fem_solver/studio/ triggers a permission
#     prompt, whatever permission mode the session is in
# Files anywhere else pass untouched.

input=$(cat)
file=$(jq -r '.tool_input.file_path // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")
[ -z "$file" ] && exit 0

root="${CLAUDE_PROJECT_DIR:-$cwd}"
case "$file" in /*) ;; *) file="$cwd/$file" ;; esac
file=$(realpath -m "$file")
rel="${file#"$(realpath -m "$root")"/}"

case "$rel" in
    fem_solver/studio/*) exit 0 ;;
    fem_solver/tests/doctest.h | fem_solver/mesh/gmsh.h)
        echo "Blocked by .claude/hooks/guard-solver.sh: $rel is a vendored third-party header and must not be edited." >&2
        exit 2
        ;;
    fem_solver/*.h | fem_solver/*.hpp | fem_solver/*.cpp | fem_solver/*.cu | fem_solver/*.cuh | fem_solver/Makefile) ;;
    *) exit 0 ;;
esac

jq -n --arg f "$rel" '{
    hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "ask",
        permissionDecisionReason: ("\($f) is part of the hand-written C++ solver. Approve only if you asked for this edit.")
    }
}'
exit 0
