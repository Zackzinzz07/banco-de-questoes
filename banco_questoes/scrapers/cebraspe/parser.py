"""Extração de itens dos cadernos da Cebraspe. Camada de parsing (CLAUDE.md 1.2).

Funções puras: recebem os bytes do PDF e devolvem modelos. Sem rede, sem banco.

Formato dos cadernos `_COM_JUSTIFICATIVA`: a banca republica a prova com o
gabarito e a justificativa oficial embutidos, item a item. Isso é melhor que o
comentário de terceiros que os sites de questões vendem — vem da fonte, já
considera anulações e alterações de recurso.

Layout: duas colunas verticais. A leitura ingênua intercala as colunas e
destrói os enunciados, então a extração recorta cada metade da página antes de
ler o texto.

O marcador do gabarito varia entre certames — vistos `JUSTIFICATIVA: CERTO.` e
`JUSTIFICATIVA - Certo.` — e alguns cadernos fecham a justificativa com um
`<FimJust>`. As duas variações são tratadas.
"""

import re

from scrapers.cebraspe import leitura_pdf

# "51 Enunciado..." no começo da linha; aceita o número colado no texto.
_ITEM = re.compile(r"(?m)^\s{0,3}(\d{1,3})\s+(?=\S)")

# "JUSTIFICATIVA: CERTO." / "JUSTIFICATIVA - Certo." / travessão.
_JUSTIFICATIVA = re.compile(
    r"JUSTIFICATIVA\s*[-–:]\s*(CERTO|ERRADO|Certo|Errado)\s*\.?\s*", re.IGNORECASE
)

_FIM_JUSTIFICATIVA = "<FimJust>"


def _limpar(texto: str) -> str:
    """Tira o marcador de fim e normaliza os espaços de quebra de linha do PDF."""
    texto = texto.replace(_FIM_JUSTIFICATIVA, " ")
    return " ".join(texto.split())


def _fatiar_em_itens(texto: str) -> list[tuple[int, str]]:
    """Quebra o texto corrido nos números de item, devolvendo (numero, bloco)."""
    marcas = list(_ITEM.finditer(texto))
    fatias = []
    for atual, marca in enumerate(marcas):
        fim = marcas[atual + 1].start() if atual + 1 < len(marcas) else len(texto)
        fatias.append((int(marca.group(1)), texto[marca.end() : fim]))
    return fatias


def extrair_itens(pdf_bytes: bytes) -> list[dict]:
    """Extrai os itens de um caderno com justificativa.

    Devolve uma lista de dicts com `numero`, `enunciado`, `gabarito`
    (`"CERTO"`/`"ERRADO"`) e `justificativa`. Blocos sem marcador de
    justificativa são descartados: sem gabarito não há item aproveitável.
    """
    texto = leitura_pdf.texto_por_coluna(pdf_bytes)
    if not texto:
        return []

    itens: list[dict] = []
    vistos: set[int] = set()

    for numero, bloco in _fatiar_em_itens(texto):
        achado = _JUSTIFICATIVA.search(bloco)
        if not achado or numero in vistos:
            continue
        enunciado = _limpar(bloco[: achado.start()])
        justificativa = _limpar(bloco[achado.end() :])
        if not enunciado:
            continue
        vistos.add(numero)
        itens.append(
            {
                "numero": numero,
                "enunciado": enunciado,
                "gabarito": achado.group(1).upper(),
                "justificativa": justificativa,
            }
        )
    return itens


# Tabela do gabarito oficial: uma linha "Item" com os numeros e a linha
# "Gabarito" logo abaixo, com C (certo), E (errado) ou X (item anulado).
_TABELA_GABARITO = re.compile(r"Item((?:\s+\d{1,3})+)\s*\n\s*Gabarito((?:\s+[CEX])+)")

_LETRA = {"C": "CERTO", "E": "ERRADO"}


def extrair_gabarito(pdf_bytes: bytes) -> dict[int, str]:
    """Le um PDF de gabarito oficial e devolve {numero_do_item: "CERTO"|"ERRADO"}.

    Itens anulados (marcados com X) ficam de fora: sem resposta certa, nao ha
    questao aproveitavel. A banca publica um arquivo por faixa de itens, entao
    o mapa cobre so o trecho daquele arquivo.
    """
    texto = leitura_pdf.texto_corrido(pdf_bytes)
    if not texto:
        return {}

    mapa: dict[int, str] = {}
    for numeros, letras in _TABELA_GABARITO.findall(texto):
        for numero, letra in zip(numeros.split(), letras.split()):
            if letra in _LETRA:
                mapa[int(numero)] = _LETRA[letra]
    return mapa


# Linhas de servico do caderno que nao pertencem a enunciado nenhum.
_RUIDO = re.compile(
    r"^\s*(\|\||CESPE\s*\||CEBRASPE\s*[-–]|--\s*CONHECIMENTOS|--\s*PROVAS|"
    r"Espaco livre|Espa\u00e7o livre)",
    re.IGNORECASE,
)


def extrair_enunciados(pdf_bytes: bytes) -> list[dict]:
    """Extrai (numero, enunciado) de um caderno de prova SEM gabarito.

    A maioria dos concursos nao publica a versao `_COM_JUSTIFICATIVA`: publica
    o caderno, com o enunciado e sem a resposta, e o gabarito oficial num
    arquivo separado. Sao duas metades da mesma questao, e o numero do item e
    a chave que as une.

    `gabarito` vem None de proposito: inventar resposta aqui seria pior que
    devolver meia questao -- quem junta e o orquestrador, com extrair_gabarito.
    """
    texto = leitura_pdf.texto_por_coluna(pdf_bytes)
    if not texto:
        return []

    itens: list[dict] = []
    vistos: set[int] = set()
    for numero, bloco in _fatiar_em_itens(texto):
        if numero in vistos:
            continue
        linhas = [linha for linha in bloco.splitlines() if not _RUIDO.match(linha)]
        enunciado = _limpar("\n".join(linhas))
        if len(enunciado) < 20:
            continue
        vistos.add(numero)
        itens.append({"numero": numero, "enunciado": enunciado, "gabarito": None})
    return itens
