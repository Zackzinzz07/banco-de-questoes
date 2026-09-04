"""Classificação dos arquivos publicados pela Cebraspe. Config estática, sem I/O.

A banca publica dezenas de arquivos por concurso (106 só na PCDF 2024) e o
nome não é confiável: certames recentes usam hash SHA-256 sem semântica
(`195BA59646CF...PDF`). A `descricaoArquivo` que a API devolve é a fonte boa —
e ainda informa a faixa de itens de cada fragmento, porque a banca fatia a
prova em vários arquivos ("PROVA OBJETIVA - ITENS DE 1 A 8").

A ordem das regras importa: `_COM_JUSTIFICATIVA` (caderno inteiro, com o
gabarito e a justificativa da banca embutidos item a item) precisa ser testado
antes de qualquer regra genérica de "justificativa", senão colide com
`JUSTIFICATIVAS_DE_ALTERACOES_DE_GABARITO`, que é outro documento — traz só os
itens mudados em recurso e renderia zero questão.
"""

import re
import unicodedata

CADERNO_COM_JUSTIFICATIVA = "caderno_com_justificativa"
JUSTIFICATIVA_DE_ALTERACAO = "justificativa_de_alteracao"
GABARITO_DEFINITIVO = "gabarito_definitivo"
GABARITO_PRELIMINAR = "gabarito_preliminar"
PADRAO_DE_RESPOSTA = "padrao_de_resposta"
CADERNO = "caderno"
EDITAL = "edital"
OUTRO = "outro"

# Tipos que rendem questão para o banco, do mais completo para o menos.
APROVEITAVEIS = (CADERNO_COM_JUSTIFICATIVA, CADERNO, GABARITO_DEFINITIVO)

_FAIXA = re.compile(r"ITENS?\s+DE\s+(\d{1,3})\s+A\s+(\d{1,3})")

# (padrão, tipo) — avaliados em ordem; o primeiro que casar decide.
_REGRAS = (
    (r"COM[_\s]?JUSTIFICATIVA", CADERNO_COM_JUSTIFICATIVA),
    (r"BONECA[_\s]?COM[_\s]?JUSTIFICATIVA", CADERNO_COM_JUSTIFICATIVA),
    (r"JUSTIFICATIVAS?\s*DE\s*(ALTERA|MANUTEN)", JUSTIFICATIVA_DE_ALTERACAO),
    (r"PADRAO\s+DE\s+RESPOSTA", PADRAO_DE_RESPOSTA),
    (r"GAB[_\s]?DEFINITIVO|GABARITOS?\s+(OFICIAIS?\s+)?DEFINITIVOS?", GABARITO_DEFINITIVO),
    (r"GAB[_\s]?PRELIMINAR|GABARITOS?\s+(OFICIAIS?\s+)?PRELIMINARES?", GABARITO_PRELIMINAR),
    (r"PROVA\s+OBJETIVA|CADERNO\s+DE\s+PROVA", CADERNO),
    (r"^EDITAL|EDITAL\s+N", EDITAL),
)


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.upper())
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def classificar(arquivo: dict) -> str:
    """Diz o tipo de um arquivo a partir do nome e da descrição.

    Devolve `outro` quando não há sinal — inventar tipo contamina a coleta com
    documento que não é prova.
    """
    alvo = _sem_acento(f"{arquivo.get('nome', '')} {arquivo.get('descricao', '')}")
    for padrao, tipo in _REGRAS:
        if re.search(padrao, alvo):
            return tipo
    if arquivo.get("origem") == "edital":
        return EDITAL
    return OUTRO


def faixa_de_itens(arquivo: dict) -> tuple[int, int] | None:
    """Extrai (primeiro, último) da descrição, quando a banca informa a faixa.

    Serve para casar um fragmento de caderno com o pedaço certo do gabarito.
    Devolve None quando a descrição não traz faixa.
    """
    achado = _FAIXA.search(_sem_acento(arquivo.get("descricao", "")))
    if not achado:
        return None
    return int(achado.group(1)), int(achado.group(2))


def aproveitaveis(arquivos: list[dict]) -> list[dict]:
    """Filtra os arquivos que rendem questão, na ordem de preferência.

    Quando o concurso publica a versão `_COM_JUSTIFICATIVA`, ela dispensa o
    gabarito separado: enunciado e resposta vêm no mesmo arquivo.
    """
    por_tipo: dict[str, list[dict]] = {}
    for arquivo in arquivos:
        tipo = classificar(arquivo)
        if tipo in APROVEITAVEIS:
            por_tipo.setdefault(tipo, []).append(arquivo)

    if CADERNO_COM_JUSTIFICATIVA in por_tipo:
        return por_tipo[CADERNO_COM_JUSTIFICATIVA]
    return por_tipo.get(CADERNO, []) + por_tipo.get(GABARITO_DEFINITIVO, [])
