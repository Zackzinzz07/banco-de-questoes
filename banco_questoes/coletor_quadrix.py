"""Coletor de provas em PDF da Quadrix: baixa, extrai questões e casa gabaritos."""
import re

import edital

RE_QUESTAO = re.compile(r"QUEST[ÃA]O\s+(\d+)")
RE_ALTERNATIVA = re.compile(r"\(([A-E])\)")


def _mapear_secoes(texto):
    """Posições onde cada matéria começa (títulos de seção em linha própria, MAIÚSCULA)."""
    marcas = []
    pos = 0
    for linha in texto.splitlines(keepends=True):
        limpa = " ".join(linha.split())
        eh_titulo = (limpa and limpa == limpa.upper() and len(limpa) <= 60
                     and any(c.isalpha() for c in limpa))
        if eh_titulo:
            for nome, dados in edital.MATERIAS.items():
                if any(padrao in limpa for padrao in dados["titulos_pdf"]):
                    marcas.append((pos, nome))
                    break
        pos += len(linha)
    return sorted(marcas)


def _materia_na_posicao(marcas, pos):
    atual = None
    for inicio, nome in marcas:
        if inicio <= pos:
            atual = nome
        else:
            break
    return atual


def _limpar(texto):
    return " ".join(texto.split()).strip()


def extrair_questoes_do_texto(texto):
    """Retorna (questoes, numeros_pulados). Questão sem 2+ alternativas é pulada."""
    marcas = _mapear_secoes(texto)
    achados = list(RE_QUESTAO.finditer(texto))
    questoes, puladas = [], []
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        corpo = texto[m.end():fim]
        numero = int(m.group(1))
        partes = RE_ALTERNATIVA.split(corpo)
        enunciado = _limpar(partes[0])
        alternativas = {}
        for letra, trecho in zip(partes[1::2], partes[2::2]):
            alternativas[letra] = _limpar(trecho)
        if not enunciado or len(alternativas) < 2:
            puladas.append(numero)
            continue
        questoes.append({
            "numero": numero,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "materia": _materia_na_posicao(marcas, m.start()),
        })
    return questoes, puladas


def extrair_gabarito_de_tabelas(tabelas):
    """Tabelas do PDF de gabarito: linha de números seguida de linha de letras."""
    gabarito = {}
    for tabela in tabelas:
        for linha_num, linha_resp in zip(tabela, tabela[1:]):
            for num, resp in zip(linha_num, linha_resp):
                num = str(num or "").strip()
                resp = str(resp or "").strip().upper()
                if num.isdigit() and len(resp) == 1 and resp in "ABCDE":
                    gabarito[int(num)] = resp
    return gabarito


def casar_gabarito(questoes, gabarito):
    for q in questoes:
        q["gabarito"] = gabarito.get(q["numero"])
