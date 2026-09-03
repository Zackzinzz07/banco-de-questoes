#!/usr/bin/env bash
# PreToolUse (Edit|Write): impede violacao das camadas do CLAUDE.md secao 1.2.
# exit 2 = bloqueia a edicao e devolve o stderr ao Claude como feedback.
#
# Nota: inspeciona o TRECHO sendo gravado, nao o arquivo inteiro. Ou seja,
# impede introduzir violacao nova; nao cobra a que ja existe. E o comportamento
# que o CLAUDE.md 1.1 descreve ("trava apenas o que for editado daqui em diante").
#
# Ha testes: .claude/hooks/testar_hooks.sh
set -uo pipefail

payload=$(cat)
arquivo=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // ""')
conteudo=$(printf '%s' "$payload" | jq -r '.tool_input.new_string // .tool_input.content // ""')

[[ "$arquivo" == *.py ]] || exit 0
[[ "$arquivo" == */tests/* ]] && exit 0

rel="${arquivo#"${CLAUDE_PROJECT_DIR:-$PWD}/"}"

# Comentarios sao prosa, nao codigo: sem isso, escrever "# antes fazia SELECT
# id FROM questoes" bloqueava a edicao.
codigo=$(sed 's/#.*//' <<<"$conteudo")

# Acesso a banco. Alem de SQL cru, pega o jeito idiomatico deste projeto:
# chamar o modulo db (db.salvar_questao(...), db.conectar()) ou importa-lo.
BANCO='\bdb\.[a-z_]+\(|^[[:space:]]*import[[:space:]]+db\b|^[[:space:]]*from[[:space:]].*[[:space:]]import[[:space:]].*\bdb\b|psycopg|sqlite3|\.execute\(|INSERT INTO|SELECT .* FROM'
DOM='BeautifulSoup|from[[:space:]]+bs4|import[[:space:]]+bs4'
REDE='requests\.|httpx\.|urlopen|page\.goto|page\.click|sync_playwright|async_playwright'

bloqueia() {
  echo "BLOQUEADO por CLAUDE.md 1.2 — $rel" >&2
  echo "$1" >&2
  exit 2
}

# --- Camada de automacao: navegacao apenas ---
if [[ "$rel" == scraper_qc.py || "$rel" == scrapers/pci/coletor*.py ]]; then
  if grep -qE "$DOM" <<<"$codigo"; then
    bloqueia "Parsing de HTML nao pertence a camada de automacao. Mova para a camada de parsing (**/parser.py)."
  fi
  if grep -qE "$BANCO" <<<"$codigo"; then
    bloqueia "Acesso a banco nao pertence a camada de automacao. Quem grava e o orquestrador, que recebe o resultado do parser."
  fi
fi

# --- Camada de parsing: funcoes puras ---
if [[ "$rel" == */parser.py || "$rel" == parser.py ]]; then
  if grep -qE "$REDE" <<<"$codigo"; then
    bloqueia "I/O de rede detectado. O parser deve ser 100% puro: recebe HTML, devolve modelos."
  fi
  if grep -qE "$BANCO" <<<"$codigo"; then
    bloqueia "Acesso a banco detectado. O parser deve ser 100% puro."
  fi
fi

# --- Camada de persistencia: sem DOM ---
if [[ "$rel" == db.py || "$rel" == scripts/importar_sqlite.py || "$rel" == migrations/* ]]; then
  if grep -qE "$DOM|select_one\(|find_all\(" <<<"$codigo"; then
    bloqueia "Seletores de DOM nao pertencem a camada de persistencia. Mova para a camada de parsing."
  fi
fi

exit 0
