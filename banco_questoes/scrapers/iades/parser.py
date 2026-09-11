"""Parser puro para cadernos e gabaritos do IADES (CLAUDE.md 1.2).

Processa bytes de PDF em memória e devolve estruturas de dados limpas.
Formato padrão do IADES: Múltipla Escolha (5 alternativas: A, B, C, D, E).
"""

import re
from typing import Any

# Regex para gabarito oficial em tabela ou lista sequencial do IADES
_GABARITO_TABELA = re.compile(
    r"(?:QUEST[ÃA]O|Item)?\s*(\d{1,3})\s*[-–:.]?\s*([A-E|X])\b",
    re.IGNORECASE,
)

# Regex para início de questão numerada (ex: "QUESTÃO 1", "1.")
_NUMERO_QUESTAO = re.compile(
    r"(?m)^\s*(?:QUEST[ÃA]O\s+)?(\d{1,3})[\s.)–-]+(?=\S)",
    re.IGNORECASE,
)

# Regex para alternativas A, B, C, D, E
_ALTERNATIVAS = re.compile(
    r"(?:\([A-E]\)|\b[A-E]\))\s+(.*?)(?=(?:\([A-E]\)|\b[A-E]\))|\Z)",
    re.DOTALL,
)

_LETRAS_VALIDAS = {"A", "B", "C", "D", "E"}


def extrair_gabarito_texto(texto: str) -> dict[int, str]:
    """Extrai gabarito a partir do texto corrido do PDF do IADES."""
    mapa = {}
    for num_str, letra in _GABARITO_TABELA.findall(texto):
        letra_norm = letra.upper()
        if letra_norm in _LETRAS_VALIDAS:
            mapa[int(num_str)] = letra_norm
    return mapa


def extrair_gabarito(conteudo_pdf: bytes) -> dict[int, str]:
    """Recebe os bytes do PDF do gabarito definitivo e devolve {numero: 'A'|'B'|'C'|'D'|'E'}."""
    try:
        from scrapers.cebraspe import leitura_pdf
        texto = leitura_pdf.texto_corrido(conteudo_pdf)
    except Exception:
        texto = ""

    if not texto:
        return {}
    return extrair_gabarito_texto(texto)


def fatiar_questoes(texto: str) -> list[tuple[int, str]]:
    """Quebra o texto corrido do caderno nas questões pelo número."""
    marcas = list(_NUMERO_QUESTAO.finditer(texto))
    fatias = []
    for i, marca in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        num = int(marca.group(1))
        fatias.append((num, texto[marca.end():fim].strip()))
    return fatias


def extrair_alternativas(bloco: str) -> tuple[str, dict[str, str]]:
    """Separa o enunciado das alternativas (A, B, C, D, E)."""
    # Procura a primeira ocorrência de (A) ou A)
    primeira_alt = re.search(r"(?:\(A\)|\bA\))\s+", bloco)
    if not primeira_alt:
        return bloco.strip(), {}

    enunciado = bloco[:primeira_alt.start()].strip()
    texto_alts = bloco[primeira_alt.start():]

    alts = {}
    matches = list(re.finditer(r"(?:\(([A-E])\)|\b([A-E])\))\s+", texto_alts))
    for i, m in enumerate(matches):
        letra = (m.group(1) or m.group(2)).upper()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto_alts)
        corpo = texto_alts[m.end():fim].strip()
        alts[letra] = " ".join(corpo.split())

    return " ".join(enunciado.split()), alts


def extrair_itens(conteudo_pdf: bytes, gabaritos: dict[int, str] | None = None) -> list[dict[str, Any]]:
    """Extrai as questões completas do caderno com suas respectivas alternativas e respostas."""
    gabaritos = gabaritos or {}
    try:
        from scrapers.cebraspe import leitura_pdf
        texto = leitura_pdf.texto_por_coluna(conteudo_pdf)
    except Exception:
        texto = ""

    if not texto:
        return []

    itens = []
    vistos = set()
    for numero, bloco in fatiar_questoes(texto):
        if numero in vistos:
            continue
        enunciado, alternativas = extrair_alternativas(bloco)
        if len(enunciado) < 15:
            continue
        vistos.add(numero)
        itens.append({
            "numero": numero,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "gabarito": gabaritos.get(numero),
            "tipo": "multipla_escolha",
        })

    return itens
