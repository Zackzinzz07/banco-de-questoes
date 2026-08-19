"""Coletor QConcursos com Playwright (bypassa CloudFlare).

Requer: pip install playwright
         playwright install chromium
"""

import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from banco_questoes import db
from banco_questoes.scrapers import http_utils
import yaml

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[ERROR] Playwright nao instalado. Execute:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

BASE_URL = "https://www.qconcursos.com/questoes-de-concursos"
MAX_PAGINAS_POR_MATERIA = 500


def carregar_editais():
    """Carrega todos os editais federais."""
    editais_dir = Path(__file__).resolve().parent.parent / "configuracoes_editais"

    editais = {}
    for arquivo in editais_dir.glob("*.yaml"):
        with open(arquivo) as f:
            config = yaml.safe_load(f)
            for exame_key, dados in config.items():
                editais[exame_key] = dados

    return editais


def extrair_questoes_pagina(html):
    """Extrai questões de uma página do QConcursos."""
    questoes = []

    # QConcursos renderizado: procurar por padrões visuais
    # Cada questão está em um container com classe question-item ou similar

    # Padrão: <div class="question-item"> ou <article class="question">
    blocos = re.findall(
        r'<(?:div|article)[^>]*(?:class="[^"]*question[^"]*"[^>]*|[^>]*id="[^"]*question[^"]*")[^>]*>.*?(?=<(?:div|article)[^>]*class="[^"]*question|$)',
        html,
        re.IGNORECASE | re.DOTALL
    )

    for bloco in blocos[:50]:  # Limitar para evitar parsing muito longo
        try:
            # Extrair enunciado (primeiro parágrafo/texto)
            match_enunciado = re.search(
                r'<(?:p|div|span)[^>]*>(.{20,500}?)</',
                bloco,
                re.DOTALL
            )

            if not match_enunciado:
                continue

            enunciado = match_enunciado.group(1)
            enunciado = re.sub(r'<[^>]+>', '', enunciado).strip()

            if len(enunciado) < 15:
                continue

            # Extrair alternativas (A) B) C) D) E) ou semelhantes)
            alt_pattern = r'(?:^|\s)([A-E])\)?\s*([^\n]+?)(?=\n|[A-E]\)|\s*<|$)'
            alternativas_matches = re.findall(alt_pattern, bloco, re.MULTILINE | re.IGNORECASE)

            alternativas = {}
            for letra, texto in alternativas_matches:
                letra = letra.upper()
                if letra in ['A', 'B', 'C', 'D', 'E']:
                    texto = re.sub(r'<[^>]+>', '', texto).strip()
                    if len(texto) > 2:
                        alternativas[letra] = texto[:200]

            if len(alternativas) < 2:
                continue

            # Extrair gabarito
            gabarito = None
            # Procurar por "Resposta:" ou "Gabarito:" seguido de letra
            match_gab = re.search(r'[Gg](?:abarito|abarit|ab\.|resposta)[:\s]+([A-E])', bloco, re.IGNORECASE)
            if match_gab:
                gabarito = match_gab.group(1).upper()

            questao = {
                'enunciado': enunciado[:500],
                'alternativas': alternativas,
                'gabarito': gabarito,
                'comentario': None,
                'ano': None,
                'prova': None,
                'fonte': 'qconcursos',
                'banca': 'QConcursos'
            }

            questoes.append(questao)

        except Exception:
            continue

    return questoes


def coletar_materia_com_playwright(page, exame_nome, materia, con):
    """Coleta questões de uma matéria usando Playwright."""

    print(f"    [{materia}] iniciando coleta...")

    chave_progresso = f"{exame_nome}/{materia}"
    pagina_inicial = db.obter_progresso(con, "qconcursos", chave_progresso) + 1

    url = f"{BASE_URL}?q={materia}"
    total_questoes = 0

    for pagina in range(pagina_inicial, MAX_PAGINAS_POR_MATERIA + 1):
        try:
            # Montar URL com paginação
            pagina_url = f"{url}&page={pagina}"

            print(f"      [page {pagina}] carregando...")
            page.goto(pagina_url, wait_until="networkidle", timeout=30000)

            # Aguardar conteúdo carregar
            page.wait_for_selector("div, article, p", timeout=10000)

            # Extrair HTML
            html = page.content()

            # Extrair questões
            questoes = extrair_questoes_pagina(html)

            if not questoes:
                print(f"      [page {pagina}] nenhuma questão encontrada")
                break

            # Salvar questões
            for q in questoes:
                db.salvar_questao(con, q)
                total_questoes += 1

            db.salvar_progresso(con, "qconcursos", chave_progresso, pagina)

            print(f"      [page {pagina}] +{len(questoes)} questoes (total: {total_questoes})")

            # Rate limit
            http_utils.aguardar(2, 4)

        except Exception as e:
            print(f"      [page {pagina}] ERRO: {str(e)[:60]}")
            break

    print(f"    [{materia}] {total_questoes} questoes coletadas")
    return total_questoes


def main():
    """Coleta questões com Playwright."""

    print("\n" + "="*60)
    print("QConcursos Coletor (Playwright - CloudFlare bypass)")
    print("="*60)

    con = db.conectar()

    try:
        editais = carregar_editais()
        total_global = 0

        # Ordem de coleta
        ordem = ['sedes_df', 'prf', 'bacen', 'receita_federal', 'inss', 'correios', 'banco_brasil']

        with sync_playwright() as p:
            # Abrir navegador
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Navegar para site primeiro (aguardar CloudFlare)
            print("[INIT] Acessando QConcursos para bypass CloudFlare...")
            try:
                page.goto("https://www.qconcursos.com/", wait_until="networkidle", timeout=30000)
                print("[INIT] CloudFlare bypass completado\n")
            except Exception as e:
                print(f"[WARN] Erro ao inicializar: {e}\n")

            # Coletar cada exame
            for exame_key in ordem:
                if exame_key not in editais:
                    continue

                exame_config = editais[exame_key]
                print(f"\n[EXAME] {exame_key}")

                cargos = exame_config.get('cargos', {})
                if not cargos:
                    continue

                cargo_nome = list(cargos.keys())[0]
                cargo_config = cargos[cargo_nome]
                materias = cargo_config.get('materias', {})

                for materia in materias:
                    total = coletar_materia_com_playwright(page, exame_key, materia, con)
                    total_global += total

            browser.close()

        print(f"\n{'='*60}")
        print(f"[FINAL] Total coletado: {total_global} questoes")
        print(f"{'='*60}\n")

    finally:
        con.close()


if __name__ == "__main__":
    main()
