"""Scraper PRF e Exames Federais - QConcursos via Playwright.

Este scraper específico coleta dos 7 exames federais:
- PRF, BACEN, Receita Federal, INSS, Correios, Banco do Brasil, SEDES_DF
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("[ERROR] Playwright nao instalado")
    sys.exit(1)

from banco_questoes import db
from banco_questoes.scrapers import http_utils
import yaml
import re
import time

# Mapeamento de exames e suas matérias no QConcursos
EXAMES = {
    'PRF': {
        'nome': 'Policial Rodoviário Federal',
        'materias': [
            'Legislação de Trânsito',
            'Direito Administrativo',
            'Direito Penal',
            'Português',
            'Conhecimentos Gerais',
            'Ética e Responsabilidade Profissional',
            'Segurança Pública',
            'Atendimento de Emergência'
        ]
    },
    'BACEN': {
        'nome': 'Banco Central do Brasil',
        'materias': [
            'Direito Administrativo',
            'Economia',
            'Contabilidade',
            'Legislação Financeira'
        ]
    },
    'Receita Federal': {
        'nome': 'Receita Federal',
        'materias': [
            'Direito Tributário',
            'Contabilidade',
            'Administração Financeira',
            'Direito Administrativo'
        ]
    },
    'INSS': {
        'nome': 'INSS',
        'materias': [
            'Direito Previdenciário',
            'Administração Pública',
            'Legislação Social'
        ]
    },
    'Correios': {
        'nome': 'Correios',
        'materias': [
            'Administração de Empresas',
            'Direito Administrativo',
            'Português'
        ]
    },
    'Banco do Brasil': {
        'nome': 'Banco do Brasil',
        'materias': [
            'Conhecimentos Bancários',
            'Matemática Financeira',
            'Português'
        ]
    }
}


def extrair_questoes_html(html):
    """Extrai questões do HTML renderizado."""
    questoes = []

    # Procurar por padrões de questões no HTML
    # QConcursos estrutura: <div class="question"> ou similar
    blocos = re.findall(
        r'<(?:div|article|section)[^>]*>.*?(?=<(?:div|article|section)[^>]*>(?:class|id).*?(?:question|questão)|$)',
        html[:100000],  # Limitar scan
        re.IGNORECASE | re.DOTALL
    )

    # Simpler approach: procurar por números seguidos de ponto (1. 2. 3. etc)
    # Indicador comum de questões em QConcursos
    linhas = html.split('\n')

    for i, linha in enumerate(linhas):
        # Procurar por enunciado (começa com número + ponto)
        if re.match(r'\s*\d+[\.\)]\s+', linha):
            try:
                enunciado = re.sub(r'<[^>]+>', '', linha).strip()
                if len(enunciado) > 15 and not enunciado.startswith('['):
                    questoes.append({
                        'enunciado': enunciado[:200],
                        'alternativas': {},
                        'gabarito': None
                    })
            except:
                pass

    return questoes[:20]  # Máximo 20 por página para segurança


def coletar_exame_prf(browser_context, exame_key, exame_config, con):
    """Coleta um exame específico."""

    print(f"\n  [EXAME] {exame_key}")
    page = browser_context.new_page()
    total = 0

    try:
        for materia in exame_config['materias']:
            print(f"    [{materia}]", end=' ', flush=True)

            try:
                # URL de busca
                url = f"https://www.qconcursos.com/questoes-de-concursos?q={materia.replace(' ', '+')}"

                # Navegar
                page.goto(url, wait_until="load", timeout=60000)
                time.sleep(2)  # Aguardar JS

                # Extrair conteúdo
                html = page.content()

                # Extrair questões
                questoes = extrair_questoes_html(html)

                if questoes:
                    for q in questoes:
                        q['fonte'] = 'qconcursos'
                        q['orgao'] = exame_key
                        q['materia'] = materia
                        db.salvar_questao(con, q)
                        total += 1

                    print(f" +{len(questoes)}")
                else:
                    print("  nenhuma")

                http_utils.aguardar(2, 3)

            except PlaywrightTimeoutError:
                print("  [TIMEOUT]")
                continue
            except Exception as e:
                print(f"  [ERRO: {str(e)[:20]}]")
                continue

    finally:
        page.close()

    print(f"    Total {exame_key}: {total}")
    return total


def main():
    """Coleta PRF e outros 6 exames federais."""

    print("\n" + "="*60)
    print("PRF + Exames Federais Scraper (Playwright)")
    print("="*60)

    con = db.conectar()

    try:
        with sync_playwright() as p:
            print("[INIT] Iniciando navegador...")
            browser = p.chromium.launch(headless=True)

            # Navegar para QConcursos primeiro (CloudFlare bypass)
            print("[INIT] Acessando QConcursos...")
            initial_page = browser.new_page()
            try:
                initial_page.goto("https://www.qconcursos.com", wait_until="load", timeout=60000)
                print("[INIT] CloudFlare bypass OK\n")
            except:
                print("[WARN] Timeout ao acessar main page, continuando...\n")
            initial_page.close()

            # Coletar cada exame
            total_global = 0
            for exame_key in ['PRF', 'BACEN', 'Receita Federal', 'INSS', 'Correios', 'Banco do Brasil']:
                if exame_key in EXAMES:
                    total = coletar_exame_prf(browser, exame_key, EXAMES[exame_key], con)
                    total_global += total

            browser.close()

        print(f"\n{'='*60}")
        print(f"[FINAL] Total coletado: {total_global} questões")
        print(f"{'='*60}\n")

    finally:
        con.close()


if __name__ == "__main__":
    main()
