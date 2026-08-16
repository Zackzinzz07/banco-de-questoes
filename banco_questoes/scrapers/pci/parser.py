"""Parsing puro do HTML do PCI Concursos: sem I/O (nem rede, nem banco).

Todas as funções aqui recebem HTML já baixado e devolvem estruturas de dados
simples, para poderem ser testadas com fixtures salvas em disco, sem precisar
de rede nem de banco de dados.
"""
import re

from bs4 import BeautifulSoup

_PADRAO_NUMERO = re.compile(r"(\d{2,})")

# Frases que indicam página de erro / categoria ou tema inexistente.
_MARCADORES_NAO_ENCONTRADO = (
    "página não encontrada",
    "pagina nao encontrada",
    "não foi encontrada",
    "not found",
)


def _pagina_nao_encontrada(html):
    """Heurística simples para detectar página de erro 404 "disfarçada"."""
    texto = html.lower()
    return any(marcador in texto for marcador in _MARCADORES_NAO_ENCONTRADO)


def descobrir_temas_do_html(html, categoria):
    """Extrai {tema_slug: url} de uma página de listagem de categoria do PCI.

    Args:
        html: HTML completo da página de listagem da categoria.
        categoria: slug da categoria (ex.: "direito-administrativo"), usado
            para restringir os links considerados aos que pertencem a ela.

    Returns:
        Dict {tema_slug: url_relativa}, ou None se a página parecer um erro
        (404 / "não encontrada") ou não tiver nenhum tema.
    """
    if not html:
        return None

    if _pagina_nao_encontrada(html):
        return None

    soup = BeautifulSoup(html, "html.parser")

    padrao_href = re.compile(rf"/simulados/{re.escape(categoria)}/([^/\"?#]+)/?$")
    temas = {}
    for link in soup.find_all("a", href=padrao_href):
        href = link.get("href", "")
        m = padrao_href.search(href)
        if not m:
            continue
        tema_slug = m.group(1)
        if tema_slug:
            temas[tema_slug] = href

    return temas or None


def _extrair_origem(origem):
    """Quebra o texto de origem ("Órgão • Banca • Ano") em campos separados."""
    banca = orgao = None
    ano = None
    if origem:
        partes = [p.strip() for p in origem.split("•")]
        if len(partes) >= 1 and partes[0]:
            orgao = partes[0]
        if len(partes) >= 2 and partes[1]:
            banca = partes[1]
        if len(partes) >= 3:
            match_ano = _PADRAO_NUMERO.search(partes[2])
            if match_ano:
                ano = int(match_ano.group(1))
    return banca, orgao, ano


def _extrair_texto_associado(bloco):
    """Extrai texto-base e imagens associadas a uma questão, se existirem.

    O PCI às vezes exibe um trecho de texto/imagem compartilhado por várias
    questões (ex.: um texto para interpretação). Quando presente, costuma
    vir em um bloco distinto do enunciado/alternativas dentro do mesmo
    container da questão.
    """
    area = bloco.select_one(
        "div.sim-texto, div.sim-texto-base, div[class*='texto-associado'], "
        "div[class*='texto-base']"
    )
    if not area:
        return "", []
    texto = area.get_text(" ", strip=True)
    imagens = [img.get("src") for img in area.find_all("img") if img.get("src")]
    return texto, imagens


def extrair_questoes_pagina(html):
    """Extrai as questões de uma página de simulado do PCI Concursos.

    Args:
        html: HTML completo da página do simulado.

    Returns:
        Lista de dicts, um por questão:
        {
            'id_pci': str,           # id único da questão (data-sid)
            'enunciado': str,
            'alternativas': {'A': str, 'B': str, ...},
            'texto_associado': str,  # texto-base compartilhado, se houver
            'imagens': [str, ...],   # URLs de imagens associadas
            'banca': str | None,
            'orgao': str | None,
            'ano': int | None,
            'prova': str | None,     # texto de origem completo, sem parse
        }
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    questoes = []

    for bloco in soup.find_all("div", class_="sim-questao"):
        sid = bloco.get("data-sid", "")
        if not sid:
            continue

        enunc_el = bloco.find("p", class_="sim-enunciado")
        enunciado = enunc_el.get_text(strip=True) if enunc_el else ""
        if not enunciado:
            continue

        alternativas = {}
        for btn in bloco.find_all("button", class_="btn-sim-alt"):
            letra = btn.get("data-letra", "")
            if not letra:
                continue
            texto_alt = btn.get_text(strip=True)
            texto_alt = re.sub(rf"^{re.escape(letra)}\s*", "", texto_alt).strip()
            alternativas[letra] = texto_alt

        if not alternativas:
            continue

        link_origem = bloco.find("a", class_="sim-prova-link")
        origem = link_origem.get_text(strip=True) if link_origem else ""
        banca, orgao, ano = _extrair_origem(origem)

        texto_associado, imagens = _extrair_texto_associado(bloco)

        questoes.append({
            "id_pci": sid,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "texto_associado": texto_associado,
            "imagens": imagens,
            "banca": banca,
            "orgao": orgao,
            "ano": ano,
            "prova": origem or None,
        })

    return questoes
