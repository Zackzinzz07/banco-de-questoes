"""Coletor QConcursos - Simples por MATÉRIA."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from banco_questoes import db
from banco_questoes import conteudo_mapper
from banco_questoes.scrapers import http_utils
import requests
import re
import json

BASE_URL = "https://www.qconcursos.com/questoes-de-concursos"
TIMEOUT = 30
MAX_PAGINAS = 500

# Matérias principais para coletar
# IMPORTANTE: Use as chaves exatas do mapeamento_conteudos.yaml (sem acentos)
MATERIAS = [
    "Portugu~es",
    "Matematica",
    "Direito Administrativo",
    "Direito Constitucional",
    "Direito Penal",
    "Conhecimentos Gerais",
    "Administracao Publica",
    "Contabilidade",
    "Economia",
    "Conhecimentos de Informatica",
    "Legislacao",
    "Etica",
]


def extrair_questoes(html):
    """Extrai questões do HTML."""
    questoes = []

    # Procurar por padrões de questão
    # QConcursos: cada questão é um bloco com texto + alternativas

    # Tenta encontrar por padrão: número + ponto + texto
    blocos = re.split(r'(?=\d+[\.\)])', html)

    for bloco in blocos[1:]:  # Skip primeiro (é header)
        try:
            # Extrair número e enunciado
            match = re.match(r'(\d+)[\.)](.*?)(?=\n[A-E][\.\)]|$)', bloco, re.DOTALL)
            if not match:
                continue

            num, enunciado = match.groups()
            enunciado = re.sub(r'<[^>]+>', '', enunciado).strip()

            if len(enunciado) < 15:
                continue

            # Extrair alternativas
            alternativas = {}
            alt_matches = re.findall(
                r'([A-E])\)?\s*([^\n]+?)(?=[A-E]\)|$)',
                bloco,
                re.MULTILINE
            )

            for letra, texto in alt_matches:
                letra = letra.upper()
                if letra in ['A', 'B', 'C', 'D', 'E']:
                    texto = re.sub(r'<[^>]+>', '', texto).strip()
                    if len(texto) > 2:
                        alternativas[letra] = texto[:200]

            if len(alternativas) < 2:
                continue

            # Gabarito
            gabarito = None
            match_gab = re.search(r'[Gg](?:abarito|ab\.?)[:\s]+([A-E])', bloco)
            if match_gab:
                gabarito = match_gab.group(1).upper()

            questao = {
                'enunciado': enunciado[:500],
                'alternativas': alternativas,
                'gabarito': gabarito,
                'comentario': None,
                'fonte': 'qconcursos',
                'banca': 'QConcursos'
            }

            questoes.append(questao)

        except Exception:
            continue

    return questoes


def coletar_materia(sessao, materia, con):
    """Coleta uma matéria do QConcursos."""

    print(f"  [{materia}]", end=' ', flush=True)

    chave = materia
    pagina_inicial = db.obter_progresso(con, "qconcursos", chave) + 1
    total = 0

    for pagina in range(pagina_inicial, MAX_PAGINAS + 1):
        try:
            # URL com busca
            url = f"{BASE_URL}?q={materia.replace(' ', '+')}&page={pagina}"

            # Fazer request com retry
            for tentativa in range(3):
                try:
                    resp = sessao.get(url, timeout=TIMEOUT)
                    resp.raise_for_status()
                    html = resp.text
                    break
                except requests.exceptions.RequestException as e:
                    if tentativa == 2:
                        raise
                    http_utils.aguardar(2, 3)
                    continue

            # Extrair questões
            questoes = extrair_questoes(html)

            if not questoes:
                print("fim", end=' ')
                break

            # Salvar cada questão com matéria + categoria sugerida
            for q in questoes:
                q['materia'] = materia
                q['assunto'] = materia

                # Tentar sugerir categoria baseado no enunciado
                categoria, confianca = conteudo_mapper.sugerir_categoria(
                    materia,
                    q.get('enunciado', '')[:200]
                )
                if categoria:
                    q['categoria'] = categoria

                # Não preencher: orgao, cargo, banca
                db.salvar_questao(con, q)
                total += 1

            db.salvar_progresso(con, "qconcursos", chave, pagina)
            print(f"{len(questoes)}", end=' ', flush=True)

            http_utils.aguardar(1, 2)

        except Exception as e:
            print(f"erro", end=' ', flush=True)
            break

    print(f" = {total}")
    return total


def main():
    """Coleta questões por matéria."""

    print("\n" + "="*60)
    print("QConcursos - Coleta por MATERIA")
    print("="*60 + "\n")

    con = db.conectar()
    sessao = http_utils.criar_sessao()

    try:
        total_global = 0

        for materia in MATERIAS:
            total = coletar_materia(sessao, materia, con)
            total_global += total

        print(f"\n{'='*60}")
        print(f"[TOTAL] {total_global:,} questoes coletadas")
        print(f"{'='*60}\n")

    finally:
        con.close()
        sessao.close()


if __name__ == "__main__":
    main()
