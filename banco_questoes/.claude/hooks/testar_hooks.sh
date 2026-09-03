#!/usr/bin/env bash
# Testes dos proprios hooks. Rode: .claude/hooks/testar_hooks.sh
# Cada caso alimenta o hook com um payload igual ao que o Claude Code envia.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1
export CLAUDE_PROJECT_DIR="$PWD"
guarda=".claude/hooks/guarda_camada.sh"
falhas=0

caso() {  # caso <descricao> <esperado> <arquivo> <conteudo>
  local desc="$1" esperado="$2" arq="$3" cont="$4"
  local payload
  payload=$(jq -nc --arg f "$PWD/$arq" --arg c "$cont" \
    '{tool_input:{file_path:$f,new_string:$c}}')
  printf '%s' "$payload" | "$guarda" >/dev/null 2>&1
  local obtido=$?
  if [[ "$obtido" == "$esperado" ]]; then
    printf '  ok    %s\n' "$desc"
  else
    printf '  FALHA %s (esperado exit %s, veio %s)\n' "$desc" "$esperado" "$obtido"
    falhas=$((falhas + 1))
  fi
}

echo "guarda_camada.sh — camada de automacao (scraper_qc.py)"
caso "bloqueia BeautifulSoup"          2 scraper_qc.py 'sopa = BeautifulSoup(html, "html.parser")'
caso "bloqueia chamada ao modulo db"   2 scraper_qc.py 'db.salvar_questao(con, q)'
caso "bloqueia import de db"           2 scraper_qc.py 'import db'
caso "bloqueia psycopg"                2 scraper_qc.py 'import psycopg2'
caso "permite Playwright"              0 scraper_qc.py 'aba.goto(url, timeout=60000)'
caso "permite comentario citando SQL"  0 scraper_qc.py '# antes fazia SELECT id FROM questoes aqui'
caso "permite docstring citando db"    0 scraper_qc.py '"""Nao grava no db: quem grava e o orquestrador."""'

echo "guarda_camada.sh — camada de automacao (coletor do PCI)"
caso "bloqueia db no coletor_v2"       2 scrapers/pci/coletor_v2.py 'db.salvar_questao(con, questao)'
caso "permite requisicao HTTP"         0 scrapers/pci/coletor_v2.py 'resposta = sessao.get(url, timeout=30)'

echo "guarda_camada.sh — camada de parsing (**/parser.py)"
caso "bloqueia rede no parser"         2 scrapers/pci/parser.py 'resposta = requests.get(url)'
caso "bloqueia banco no parser"        2 scrapers/pci/parser.py 'con.execute("SELECT 1")'
caso "permite BeautifulSoup"           0 scrapers/pci/parser.py 'sopa = BeautifulSoup(html, "html.parser")'

echo "guarda_camada.sh — camada de persistencia (db.py)"
caso "bloqueia seletor de DOM"         2 db.py 'bloco.select_one(".q-id")'
caso "permite SQL"                     0 db.py 'con.execute("SELECT * FROM questoes")'

echo "guarda_camada.sh — isencoes"
caso "ignora arquivo de teste"         0 tests/test_scraper_qc.py 'sopa = BeautifulSoup(html)'
caso "ignora arquivo nao-Python"       0 README.md 'BeautifulSoup'

echo
if (( falhas )); then
  echo "$falhas caso(s) falhando."
  exit 1
fi
echo "todos os casos passaram."
