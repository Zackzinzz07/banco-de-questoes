#!/usr/bin/env bash
# PostToolUse (Edit|Write): aplica ruff format + ruff check --fix no arquivo tocado.
set -uo pipefail

arquivo=$(jq -r '.tool_input.file_path // ""')
[[ "$arquivo" == *.py && -f "$arquivo" ]] || exit 0

raiz="${CLAUDE_PROJECT_DIR:-$PWD}"
ruff_bin="$raiz/.venv/bin/ruff"
[[ -x "$ruff_bin" ]] || ruff_bin=$(command -v ruff) || exit 0

"$ruff_bin" format "$arquivo" >/dev/null 2>&1
"$ruff_bin" check --fix --select I "$arquivo" >/dev/null 2>&1
exit 0
