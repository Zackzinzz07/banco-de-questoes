#!/usr/bin/env bash
# PostToolUse (Edit|Write): limites do CLAUDE.md secao 1.1.
# exit 2 devolve o aviso ao Claude, que deve fatiar antes de seguir.
#
# So reclama quando o arquivo CRESCEU em relacao ao commit atual. Sem isso,
# corrigir uma linha num arquivo que ja nasceu grande disparava o alerta toda
# vez, contrariando o proprio CLAUDE.md 1.1: "o hook trava apenas o que for
# editado daqui em diante — nao e para refatorar tudo de uma vez".
set -uo pipefail

arquivo=$(jq -r '.tool_input.file_path // ""')
[[ "$arquivo" == *.py && -f "$arquivo" ]] || exit 0
[[ "$arquivo" == */tests/* ]] && exit 0

raiz="${CLAUDE_PROJECT_DIR:-$PWD}"
rel="${arquivo#"$raiz/"}"

limite=350
[[ "$rel" == scrapers/* || "$rel" == simulados/estilos/* ]] && limite=250
[[ "$rel" == main.py || "$rel" == simulados/cli_multibanca.py ]] && limite=60

linhas=$(wc -l < "$arquivo")
(( linhas > limite )) || exit 0

# Quantas linhas o arquivo tinha no ultimo commit? Ausente (arquivo novo) = 0.
antes=$(git -C "$raiz" show "HEAD:./$rel" 2>/dev/null | wc -l)

if (( linhas <= antes )); then
  # Ja estava acima do limite e nao cresceu: divida conhecida, segue o jogo.
  exit 0
fi

echo "LIMITE CLAUDE.md 1.1 — $rel esta com $linhas linhas (max $limite)." >&2
if (( antes > 0 )); then
  echo "Cresceu $(( linhas - antes )) linha(s) nesta edicao (antes: $antes)." >&2
fi
echo "Fatie o arquivo em modulos coesos antes de continuar. Use /fatiar $rel se precisar de um plano." >&2
exit 2
