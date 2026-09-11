"""Parser puro para cadernos e gabaritos do Instituto AOCP (CLAUDE.md 1.2).

Processa bytes de PDF em memória e devolve estruturas de dados limpas.
Formato padrão do Instituto AOCP: Múltipla Escolha (5 alternativas: A, B, C, D, E).
"""

import re
from typing import Any

from bs4 import BeautifulSoup

# Regex para gabarito oficial em tabela ou lista do Instituto AOCP
_GABARITO_TABELA = re.compile(
    r"(?:QUEST[ÃA]O|Item)?\s*(\d{1,3})\s*[-–:.]?\s*([A-E|X])\b",
    re.IGNORECASE,
)

# Regex para início de questão numerada (ex: "QUESTÃO 01", "1.")
_NUMERO_QUESTAO = re.compile(
    r"(?m)^\s*(?:QUEST[ÃA]O\s+)?(\d{1,3})[\s.)–-]+(?=\S)",
    re.IGNORECASE,
)

_LETRAS_VALIDAS = {"A", "B", "C", "D", "E"}


def extrair_gabarito_texto(texto: str) -> dict[int, str]:
    """Extrai gabarito a partir do texto corrido do PDF do Instituto AOCP."""
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
    primeira_alt = re.search(r"(?:\([A-E]\)|\b[A-E]\))\s+", bloco)
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


def extrair_concursos_html(html: str) -> list[dict[str, str]]:
    """Extrai {id, orgao, descricao} dos cartões de concurso de uma página de listagem."""
    soup = BeautifulSoup(html, "html.parser")
    concursos = []
    vistos: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"^/concursos/\d+$")):
        concurso_id = a["href"].rsplit("/", 1)[-1]
        if concurso_id in vistos:
            continue
        vistos.add(concurso_id)
        titulo = a.find("h1")
        descricao = a.find("p")
        concursos.append({
            "id": concurso_id,
            "orgao": titulo.get_text(strip=True) if titulo else "",
            "descricao": descricao.get_text(strip=True) if descricao else "",
        })
    return concursos


def extrair_publicacoes_html(html: str) -> list[dict[str, str]]:
    """Extrai as publicações (editais, comunicados etc.) da página de um concurso."""
    soup = BeautifulSoup(html, "html.parser")
    publicacoes = []
    for a in soup.find_all("a", href=re.compile(r"arquivos-site\.institutoaocp\.org\.br")):
        texto = " ".join(a.get_text().split())
        publicacoes.append({"texto": texto, "url": a["href"]})
    return publicacoes


def extrair_edital_abertura(publicacoes: list[dict[str, str]]) -> dict[str, str] | None:
    """Escolhe o edital de abertura entre as publicações (filtro estrito, Zero-Lixo)."""
    candidatos = [
        p for p in publicacoes
        if "EDITAL" in p["texto"].upper() and "ABERTURA" in p["texto"].upper()
    ]
    if not candidatos:
        return None
    # A página lista as publicações em ordem cronológica decrescente, então a
    # primeira candidata é a retificação mais recente do edital de abertura.
    return candidatos[0]


def extrair_link_visualizar_prova(html: str) -> str | None:
    """Extrai o link da ferramenta de visualização de cadernos/gabarito, se publicada."""
    soup = BeautifulSoup(html, "html.parser")
    a = soup.find("a", href=re.compile(r"open-link\?identificador="))
    return a["href"] if a else None


def extrair_opcoes_prova(html: str) -> tuple[list[str], list[str]]:
    """Extrai os cargos e tipos de prova disponíveis nos <select> do visualizador."""
    soup = BeautifulSoup(html, "html.parser")
    select_cargo = soup.find("select", id="cargo")
    select_tipo = soup.find("select", id="tipo_prova")
    cargos = [
        o.get_text(strip=True)
        for o in (select_cargo.find_all("option") if select_cargo else [])
        if o.get_text(strip=True).upper() != "SELECIONE"
    ]
    tipos = [
        o.get_text(strip=True)
        for o in (select_tipo.find_all("option") if select_tipo else [])
        if o.get_text(strip=True).upper() != "SELECIONE"
    ]
    return cargos, tipos


def extrair_gabarito_html(html: str) -> dict[int, str]:
    """Extrai o gabarito da grade HTML renderizada -- aqui não existe PDF de gabarito.

    Questões anuladas aparecem na grade sem a letra dentro de <strong>; são
    ignoradas (ficam de fora do dicionário) em vez de quebrar o parsing.
    """
    soup = BeautifulSoup(html, "html.parser")
    mapa: dict[int, str] = {}
    for linha in soup.select("div.row"):
        celulas = linha.find_all("div", class_="col-md-6")
        if len(celulas) != 2:
            continue
        num_texto = celulas[0].get_text(strip=True)
        letra_texto = celulas[1].get_text(strip=True).upper()
        if num_texto.isdigit() and letra_texto in _LETRAS_VALIDAS:
            mapa[int(num_texto)] = letra_texto
    return mapa
