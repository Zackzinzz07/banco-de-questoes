"""Leitura de PDF em ordem de leitura. Funcoes puras sobre bytes.

Separado de `parser.py` porque sao assuntos distintos: aqui e "como transformar
a geometria da pagina em texto na ordem certa"; la e "como interpretar o
formato de item da Cebraspe".

Os cadernos usam duas colunas mas intercalam linhas de largura total -- o
comando "julgue os itens a seguir" e enunciados longos. Recortar a pagina ao
meio partia essas linhas e embaralhava os blocos, e o item 40 do caderno da
PCDF 2024 sumia da extracao.

Gabarito e caso a parte: e TABELA, nao prosa em colunas. Separar em colunas
desalinha o pareamento Item/Gabarito (medido: 77 de 120 itens contra 112
lendo em largura total), por isso `texto_corrido`.
"""

import io

import pdfplumber


def calha(palavras, largura: float) -> float:
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


def agrupar_por_altura(palavras, tolerancia: float = 3.0) -> list[list]:
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


def classificar_linhas(linhas, corte: float) -> list[tuple[str, list]]:
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


def texto_da_pagina(pagina) -> str:
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
    corte = calha(palavras, pagina.width)

    saida: list[str] = []
    esquerda: list[str] = []
    direita: list[str] = []

    def esvaziar() -> None:
        saida.extend(esquerda)
        saida.extend(direita)
        esquerda.clear()
        direita.clear()

    for lado, linha in classificar_linhas(agrupar_por_altura(palavras), corte):
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


def texto_por_coluna(pdf_bytes: bytes) -> str:
    """Concatena o texto de todas as páginas na ordem de leitura.

    Devolve string vazia se o PDF não abrir — layout quebrado não pode derrubar
    a coleta inteira (CLAUDE.md 3).
    """
    if not pdf_bytes:
        return ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(texto_da_pagina(pagina) for pagina in pdf.pages)
    except Exception:
        return ""


def texto_corrido(pdf_bytes: bytes) -> str:
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
