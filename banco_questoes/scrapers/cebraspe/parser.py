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

import io
import re

import pdfplumber

# "51 Enunciado..." no começo da linha; aceita o número colado no texto.
_ITEM = re.compile(r"(?m)^\s{0,3}(\d{1,3})\s+(?=\S)")

# "JUSTIFICATIVA: CERTO." / "JUSTIFICATIVA - Certo." / travessão.
_JUSTIFICATIVA = re.compile(
    r"JUSTIFICATIVA\s*[-–:]\s*(CERTO|ERRADO|Certo|Errado)\s*\.?\s*", re.IGNORECASE
)

_FIM_JUSTIFICATIVA = "<FimJust>"


def _calha(palavras, largura: float) -> float:
    """Devolve o x da calha: o ponto do miolo que menos palavras atravessam.

    Medir por pixel vazio nao serve: uma unica linha de largura total (a caixa
    de instrucoes da capa, por exemplo) tapa a calha e faz a pagina inteira
    parecer de coluna unica.
    """
    inicio, fim = int(largura * 0.35), int(largura * 0.65)
    melhor_x, menos = largura / 2, len(palavras) + 1
    for x in range(inicio, fim):
        cruzam = sum(1 for p in palavras if p["x0"] < x < p["x1"])
        if cruzam < menos:
            menos, melhor_x = cruzam, x
    return melhor_x


def _agrupar_por_altura(palavras, tolerancia: float = 3.0) -> list[list]:
    """Agrupa palavras em linhas visuais, tolerando variacao fracionaria de topo."""
    if not palavras:
        return []
    ordenadas = sorted(palavras, key=lambda p: (p["top"], p["x0"]))
    linhas, atual = [], [ordenadas[0]]
    for palavra in ordenadas[1:]:
        if abs(palavra["top"] - atual[0]["top"]) <= tolerancia:
            atual.append(palavra)
        else:
            linhas.append(sorted(atual, key=lambda p: p["x0"]))
            atual = [palavra]
    linhas.append(sorted(atual, key=lambda p: p["x0"]))
    return linhas


def _classificar(linhas, corte: float) -> list[tuple[str, list]]:
    """Rotula cada linha como `esquerda`, `direita` ou `inteira`.

    Numa pagina de duas colunas as linhas das duas colunas ficam na mesma
    altura, entao um grupo de altura vira DUAS linhas. So e de largura total o
    grupo em que alguma palavra atravessa a calha.
    """
    saida = []
    for linha in linhas:
        if any(p["x0"] < corte < p["x1"] for p in linha):
            saida.append(("inteira", linha))
            continue
        esquerda = [p for p in linha if p["x1"] <= corte]
        direita = [p for p in linha if p["x0"] >= corte]
        if esquerda:
            saida.append(("esquerda", esquerda))
        if direita:
            saida.append(("direita", direita))
    return saida


def _texto_da_pagina(pagina) -> str:
    """Le uma pagina de duas colunas com linhas de largura total intercaladas.

    Os cadernos da Cebraspe usam duas colunas, mas intercalam linhas que cruzam
    a calha -- o comando "julgue os itens a seguir" e enunciados longos. Uma
    dessas linhas fecha o trecho anterior: esvazia a coluna esquerda, depois a
    direita, e so entao entra. Recortar a pagina ao meio partia essas linhas e
    embaralhava os blocos -- foi assim que o item 40 do caderno da PCDF 2024
    sumia da extracao.
    """
    palavras = pagina.extract_words()
    if not palavras:
        return ""
    corte = _calha(palavras, pagina.width)

    saida: list[str] = []
    esquerda: list[str] = []
    direita: list[str] = []

    def esvaziar() -> None:
        saida.extend(esquerda)
        saida.extend(direita)
        esquerda.clear()
        direita.clear()

    for lado, linha in _classificar(_agrupar_por_altura(palavras), corte):
        texto = " ".join(p["text"] for p in linha)
        if lado == "esquerda":
            esquerda.append(texto)
        elif lado == "direita":
            direita.append(texto)
        else:
            esvaziar()
            saida.append(texto)
    esvaziar()
    return "\n".join(saida)


def _texto_por_coluna(pdf_bytes: bytes) -> str:
    """Concatena o texto de todas as páginas na ordem de leitura.

    Devolve string vazia se o PDF não abrir — layout quebrado não pode derrubar
    a coleta inteira (CLAUDE.md 3).
    """
    if not pdf_bytes:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(_texto_da_pagina(pagina) for pagina in pdf.pages)
    except Exception:
        return ""


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
    texto = _texto_por_coluna(pdf_bytes)
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


def _texto_corrido(pdf_bytes: bytes) -> str:
    """Le o PDF em largura total, sem separar colunas.

    O gabarito e uma TABELA que atravessa a pagina: separar em colunas parte as
    linhas "Item"/"Gabarito" e desalinha o pareamento (medido: 77 de 120 itens
    contra 112 lendo em largura total).
    """
    if not pdf_bytes:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)
    except Exception:
        return ""


def extrair_gabarito(pdf_bytes: bytes) -> dict[int, str]:
    """Le um PDF de gabarito oficial e devolve {numero_do_item: "CERTO"|"ERRADO"}.

    Itens anulados (marcados com X) ficam de fora: sem resposta certa, nao ha
    questao aproveitavel. A banca publica um arquivo por faixa de itens, entao
    o mapa cobre so o trecho daquele arquivo.
    """
    texto = _texto_corrido(pdf_bytes)
    if not texto:
        return {}

    mapa: dict[int, str] = {}
    for numeros, letras in _TABELA_GABARITO.findall(texto):
        for numero, letra in zip(numeros.split(), letras.split()):
            if letra in _LETRA:
                mapa[int(numero)] = _LETRA[letra]
    return mapa
