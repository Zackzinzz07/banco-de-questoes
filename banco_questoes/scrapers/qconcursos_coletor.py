"""Coletor QConcursos: Extrai questões dos 6 exames federais + SEDES DF."""

import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from banco_questoes import db
from banco_questoes.scrapers import http_utils
import yaml

BASE_URL = "https://www.qconcursos.com/questoes-de-concursos"
MAX_PAGINAS_POR_MATERIA = 500
TIMEOUT = 10


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

    # QConcursos struct: <div class="question"> ... <span class="question-text">
    # Padrão mais genérico - busca por divs com class contendo "question"

    # Buscar blocos de questões (varia por layout do site)
    blocos = re.findall(
        r'<div[^>]*class="[^"]*questão[^"]*"[^>]*>.*?(?=<div[^>]*class="[^"]*questão|$)',
        html,
        re.IGNORECASE | re.DOTALL
    )

    if not blocos:
        # Fallback: procurar por "question" ou padrões de enunciado
        blocos = re.findall(
            r'<div[^>]*class="[^"]*question[^"]*"[^>]*>.*?(?=<div|<section|$)',
            html,
            re.IGNORECASE | re.DOTALL
        )

    for bloco in blocos:
        try:
            # Extrair enunciado
            match_enunciado = re.search(
                r'<[^>]*(?:class|id)[^>]*enunciado[^>]*>(.+?)</',
                bloco,
                re.IGNORECASE | re.DOTALL
            )
            if not match_enunciado:
                match_enunciado = re.search(
                    r'<(?:p|div|span)[^>]*>(.+?)</',
                    bloco,
                    re.DOTALL
                )

            if not match_enunciado:
                continue

            enunciado = match_enunciado.group(1)
            enunciado = re.sub(r'<[^>]+>', '', enunciado).strip()

            if len(enunciado) < 10:
                continue

            # Extrair alternativas (A, B, C, D, E)
            alternativas_matches = re.findall(
                r'[A\(\)\s]*([A-E])\s*[\):\-]\s*(.+?)(?=[A-E]\s*[\):\-]|$)',
                bloco,
                re.IGNORECASE | re.DOTALL
            )

            if not alternativas_matches:
                continue

            alternativas = {}
            for letra, texto in alternativas_matches:
                letra = letra.upper()
                if letra in ['A', 'B', 'C', 'D', 'E']:
                    texto = re.sub(r'<[^>]+>', '', texto).strip()
                    alternativas[letra] = texto

            if len(alternativas) < 2:
                continue

            # Extrair gabarito (se houver)
            gabarito = None
            match_gab = re.search(r'[Gg]abarito[:\s]+([A-E])', bloco)
            if match_gab:
                gabarito = match_gab.group(1).upper()

            # Extrair comentário
            comentario = None
            match_com = re.search(
                r'[Cc]oment[áa]rio[:\s]+(.+?)(?=<(?:hr|br|div|p)|$)',
                bloco,
                re.DOTALL
            )
            if match_com:
                comentario = re.sub(r'<[^>]+>', '', match_com.group(1)).strip()

            # Extrair ano/prova (se houver)
            ano = None
            prova = None
            match_ano = re.search(r'(\d{4})', enunciado + bloco)
            if match_ano:
                ano = int(match_ano.group(1))

            questao = {
                'enunciado': enunciado[:500],
                'alternativas': alternativas,
                'gabarito': gabarito,
                'comentario': comentario,
                'ano': ano,
                'prova': prova,
                'banca': 'QConcursos'  # Será sobrescrito por edital
            }

            questoes.append(questao)

        except Exception as e:
            continue

    return questoes


def coletar_exame(sessao, exame_nome, exame_config, con):
    """Coleta questões de um exame federal específico."""

    print(f"\n{'='*60}")
    print(f"[EXAME] {exame_nome} ({exame_config['banca']})")
    print(f"{'='*60}")

    cargos = exame_config.get('cargos', {})
    if not cargos:
        print(f"  [SKIP] Nenhum cargo configurado")
        return 0

    # Pegar primeiro cargo
    cargo_nome = list(cargos.keys())[0]
    cargo_config = cargos[cargo_nome]
    materias = cargo_config.get('materias', {})

    total_questoes = 0

    for materia, quantidade_esperada in materias.items():
        print(f"\n  [{materia}] (esperado: {quantidade_esperada})")

        # Montar URL para filtrar por exame + materia
        # QConcursos: /questoes-de-concursos/materia/Direito+Administrativo
        chave_progresso = f"{exame_nome}/{materia}"
        pagina_inicial = db.obter_progresso(con, "qconcursos", chave_progresso) + 1

        questoes_materia = 0

        for pagina in range(pagina_inicial, MAX_PAGINAS_POR_MATERIA + 1):
            # Monta URL (QConcursos simples)
            url = f"{BASE_URL}"

            # Parâmetros de busca
            params = {
                'q': materia,
                'page': pagina
            }

            try:
                resp = sessao.get(url, params=params, timeout=sessao.timeout)
                resp.raise_for_status()
                html = resp.text

                if not html:
                    print(f"    [page {pagina}] nenhuma resposta")
                    break

                questoes_pagina = extrair_questoes_pagina(html)
                if not questoes_pagina:
                    print(f"    [page {pagina}] nenhuma questão encontrada")
                    break

                # Salvar questões com metadados do edital
                for q in questoes_pagina:
                    q['fonte'] = 'qconcursos'
                    q['banca'] = exame_config.get('banca', 'QConcursos')
                    q['orgao'] = exame_config.get('orgao', exame_nome)
                    q['cargo'] = cargo_nome
                    q['materia'] = materia
                    q['assunto'] = materia  # Por enquanto materia = assunto

                    db.salvar_questao(con, q)
                    questoes_materia += 1

                # Atualizar progresso
                db.salvar_progresso(con, "qconcursos", chave_progresso, pagina)

                print(f"    [page {pagina}] +{len(questoes_pagina)} questoes (total: {questoes_materia})")

                http_utils.aguardar(1)  # Rate limit

            except Exception as e:
                print(f"    [page {pagina}] ERRO: {str(e)[:60]}")
                continue

        total_questoes += questoes_materia

    print(f"\n  [TOTAL] {total_questoes} questoes coletadas para {exame_nome}")
    return total_questoes


def main():
    """Coleta questões de todos os exames federais."""

    print("\n" + "="*60)
    print("QConcursos Coletor - Exames Federais")
    print("="*60)

    con = db.conectar()
    sessao = http_utils.criar_sessao()

    try:
        editais = carregar_editais()
        total_global = 0

        # Ordem de coleta
        ordem = ['sedes_df', 'prf', 'bacen', 'receita_federal', 'inss', 'correios', 'banco_brasil']

        for exame_key in ordem:
            if exame_key not in editais:
                continue

            exame_config = editais[exame_key]
            total = coletar_exame(sessao, exame_key, exame_config, con)
            total_global += total

        print(f"\n{'='*60}")
        print(f"[FINAL] Total coletado: {total_global} questoes")
        print(f"{'='*60}\n")

    finally:
        con.close()
        sessao.close()


if __name__ == "__main__":
    main()
