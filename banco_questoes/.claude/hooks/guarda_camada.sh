#!/usr/bin/env bash
# PreToolUse (Edit|Write): impede violacao das camadas do CLAUDE.md secao 1.2.
# exit 2 = bloqueia a edicao e devolve o stderr ao Claude como feedback.
set -uo pipefail

payload=$(cat)
arquivo=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // ""')
conteudo=$(printf '%s' "$payload" | jq -r '.tool_input.new_string // .tool_input.content // ""')

[[ "$arquivo" == *.py ]] || exit 0
[[ "$arquivo" == */tests/* ]] && exit 0

rel="${arquivo#"${CLAUDE_PROJECT_DIR:-$PWD}/"}"

bloqueia() {
  echo "BLOQUEADO por CLAUDE.md 1.2 — $rel" >&2
  echo "$1" >&2
  exit 2
}

# --- Camada de automacao: Playwright apenas ---
if [[ "$rel" == scraper_qc.py || "$rel" == scrapers/qconcursos_*.py \
   || "$rel" == scrapers/prf_federal_scraper.py || "$rel" == scrapers/pci/coletor*.py ]]; then
  if grep -qiE 'BeautifulSoup|from[[:space:]]+bs4|import[[:space:]]+bs4' <<<"$conteudo"; then
    bloqueia "Parsing de HTML nao pertence a camada de automacao. Mova para a camada de parsing (**/parser.py)."
  fi
  if grep -qiE 'sqlite3|psycopg|\.execute\(|INSERT INTO|SELECT .* FROM' <<<"$conteudo"; then
    bloqueia "Acesso a banco nao pertence a camada de automacao. Mova para db.py."
  fi
fi

# --- Camada de parsing: funcoes puras ---
if [[ "$rel" == */parser.py || "$rel" == parser.py ]]; then
  if grep -qiE 'requests\.|httpx\.|urlopen|page\.goto|page\.click|sync_playwright|async_playwright' <<<"$conteudo"; then
    bloqueia "I/O de rede detectado. O parser deve ser 100% puro: recebe HTML, devolve modelos."
  fi
  if grep -qiE 'sqlite3|psycopg|\.execute\(|INSERT INTO' <<<"$conteudo"; then
    bloqueia "Acesso a banco detectado. O parser deve ser 100% puro."
  fi
fi

# --- Camada de persistencia: sem DOM ---
if [[ "$rel" == db.py || "$rel" == scripts/importar_sqlite.py || "$rel" == migrations/* ]]; then
  if grep -qiE 'BeautifulSoup|from[[:space:]]+bs4|select_one\(|find_all\(' <<<"$conteudo"; then
    bloqueia "Seletores de DOM nao pertencem a camada de persistencia. Mova para a camada de parsing."
  fi
fi

exit 0
