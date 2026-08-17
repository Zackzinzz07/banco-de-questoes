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


def descobrir_subcategorias_do_html(html, categoria):
    """Extrai hierarquia completa: subcategoria → temas.

    PCI structure: /simulados/categoria/subcategoria/tema (opcional)

    Args:
        html: HTML da página principal de simulados.
        categoria: slug da categoria.

    Returns:
        Dict {
            "subcategoria_slug": {
                "nome": "Nome da Subcategoria",
                "url": "/simulados/cat/subcat",
                "temas": [
                    {"nome": "Tema 1", "url": "/simulados/cat/subcat/tema1", "slug": "tema1"},
                    ...
                ]
            },
            ...
        }
    """
    if not html or _pagina_nao_encontrada(html):
        return {}

    soup = BeautifulSoup(html, "html.parser")
    subcategorias = {}

    # Padrão para links de subcategoria: /simulados/categoria/subcategoria
    padrao_subcat = re.compile(rf"/simulados/{re.escape(categoria)}/([^/\"?#]+)/?$")
    # Padrão para links de tema: /simulados/categoria/subcategoria/tema
    padrao_tema = re.compile(rf"/simulados/{re.escape(categoria)}/([^/\"?#]+)/([^/\"?#]+)/?$")

    links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href", "")
        texto = link.get_text(strip=True)

        if not href or f"/simulados/{categoria}/" not in href:
            continue

        # Verificar se é tema (3+ partes)
        m_tema = padrao_tema.search(href)
        if m_tema:
            subcat_slug = m_tema.group(1)
            tema_slug = m_tema.group(2)

            if subcat_slug not in subcategorias:
                subcategorias[subcat_slug] = {
                    "nome": subcat_slug.replace("-", " ").title(),
                    "url": f"/simulados/{categoria}/{subcat_slug}",
                    "slug": subcat_slug,
                    "temas": [],
                }

            tema = {
                "nome": texto,
                "url": href,
                "slug": tema_slug,
            }
            if tema not in subcategorias[subcat_slug]["temas"]:
                subcategorias[subcat_slug]["temas"].append(tema)
            continue

        # Verificar se é subcategoria (2 partes)
        m_subcat = padrao_subcat.search(href)
        if m_subcat:
            subcat_slug = m_subcat.group(1)

            if subcat_slug not in subcategorias:
                subcategorias[subcat_slug] = {
                    "nome": texto,
                    "url": href,
                    "slug": subcat_slug,
                    "temas": [],
                }

    return subcategorias


def descobrir_temas_do_html(html, categoria):
    """Extrai {tema_slug: url} de uma página de listagem de categoria do PCI.

    DEPRECATED: Use descobrir_subcategorias_do_html() para obter hierarquia completa.
    Esta função mantida para compatibilidade com código antigo.

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

    # Usar nova função e converter resultado
    subcats = descobrir_subcategorias_do_html(html, categoria)
    if not subcats:
        return None

    # Extrair todos os temas de todas as subcategorias
    temas = {}
    for subcat_data in subcats.values():
        for tema in subcat_data["temas"]:
            temas[tema["slug"]] = tema["url"]

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


def _extrair_todas_imagens(bloco):
    """Extrai TODAS as imagens de um bloco de questão (enunciado + alternativas + texto associado).

    Returns:
        list: URLs de imagens (strings), deduplicated
    """
    urls = set()

    # Imagens do enunciado
    for img in bloco.find_all("img"):
        src = img.get("src")
        if src:
            # Normalizar URL absoluta
            if not src.startswith("http"):
                src = f"https://www.pciconcursos.com.br{src}"
            urls.add(src)

    # background-image em style
    for el in bloco.find_all(style=True):
        style = el.get("style", "")
        if "background-image" in style:
            match = re.search(r"url\(['\"]?([^'\")+]+)['\"]?\)", style)
            if match:
                url = match.group(1)
                if not url.startswith("http"):
                    url = f"https://www.pciconcursos.com.br{url}"
                urls.add(url)

    return list(urls)


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

        # Extrair TODAS as imagens (incluindo enunciado + alternativas + texto associado)
        todas_imagens = _extrair_todas_imagens(bloco)

        questoes.append({
            "id_pci": sid,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "texto_associado": texto_associado,
            "imagens": imagens,  # Mantém para compatibilidade
            "imagens_urls": todas_imagens,  # Nova: todas as imagens de uma vez
            "banca": banca,
            "orgao": orgao,
            "ano": ano,
            "prova": origem or None,
        })

    return questoes
