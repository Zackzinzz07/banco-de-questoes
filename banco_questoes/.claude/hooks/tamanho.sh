#!/usr/bin/env bash
# PostToolUse (Edit|Write): limites do CLAUDE.md secao 1.1.
# exit 2 devolve o aviso ao Claude, que deve fatiar antes de seguir.
set -uo pipefail

arquivo=$(jq -r '.tool_input.file_path // ""')
[[ "$arquivo" == *.py && -f "$arquivo" ]] || exit 0
[[ "$arquivo" == */tests/* ]] && exit 0

rel="${arquivo#"${CLAUDE_PROJECT_DIR:-$PWD}/"}"

limite=350
[[ "$rel" == scrapers/* || "$rel" == simulados/estilos/* ]] && limite=250
[[ "$rel" == main.py || "$rel" == simulados/cli_multibanca.py ]] && limite=60

linhas=$(wc -l < "$arquivo")
if (( linhas > limite )); then
  echo "LIMITE CLAUDE.md 1.1 — $rel esta com $linhas linhas (max $limite)." >&2
  echo "Fatie o arquivo em modulos coesos antes de continuar. Use /fatiar $rel se precisar de um plano." >&2
  exit 2
fi
exit 0
