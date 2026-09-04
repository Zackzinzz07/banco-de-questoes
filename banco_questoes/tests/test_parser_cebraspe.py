"""Testes do parser de cadernos da Cebraspe (PDF -> itens tipados).

A fixture é o caderno da PCDF 2024 (Conhecimentos Específicos, cargo 1) na
versão republicada `_COM_JUSTIFICATIVA`, que traz enunciado, gabarito oficial
e a justificativa da própria banca — item a item.

Medido na fixture antes de escrever o teste: 70 itens, numerados de 51 a 120,
35 CERTO e 35 ERRADO, com 70 marcadores `<FimJust>`.
"""

from pathlib import Path

import pytest

from scrapers.cebraspe import leitura_pdf, parser

FIXTURE = Path(__file__).parent / "fixtures" / "cebraspe_com_justificativa.pdf"


@pytest.fixture
def pdf_bytes():
    if not FIXTURE.exists():
        pytest.skip("fixture cebraspe_com_justificativa.pdf ainda não baixada")
    return FIXTURE.read_bytes()


def test_extrai_todos_os_itens_do_caderno(pdf_bytes):
    itens = parser.extrair_itens(pdf_bytes)
    assert len(itens) == 70


def test_cada_item_tem_numero_enunciado_e_gabarito(pdf_bytes):
    itens = parser.extrair_itens(pdf_bytes)
    for item in itens:
        assert item["numero"] > 0
        assert item["enunciado"].strip()
        assert item["gabarito"] in ("CERTO", "ERRADO")


def test_gabaritos_batem_com_a_contagem_do_caderno(pdf_bytes):
    itens = parser.extrair_itens(pdf_bytes)
    gabaritos = [i["gabarito"] for i in itens]
    assert gabaritos.count("CERTO") == 35
    assert gabaritos.count("ERRADO") == 35


def test_numeracao_preserva_a_do_caderno(pdf_bytes):
    """O caderno começa no item 51 (é o bloco de Específicos, não o de Básicos)."""
    numeros = [i["numero"] for i in parser.extrair_itens(pdf_bytes)]
    assert min(numeros) == 51
    assert max(numeros) == 120
    assert len(set(numeros)) == 70, "houve número de item repetido"


def test_justificativa_oficial_vem_junto(pdf_bytes):
    itens = parser.extrair_itens(pdf_bytes)
    com_justificativa = [i for i in itens if i["justificativa"].strip()]
    assert len(com_justificativa) == 70


def test_marcador_interno_fimjust_nao_vaza_para_o_texto(pdf_bytes):
    """`<FimJust>` delimita o fim da justificativa no PDF; é ruído de layout."""
    for item in parser.extrair_itens(pdf_bytes):
        assert "<FimJust>" not in item["justificativa"]
        assert "<FimJust>" not in item["enunciado"]
        assert "JUSTIFICATIVA" not in item["enunciado"]


def test_item_conhecido_sai_correto(pdf_bytes):
    """Item 65 trata das fases da licitação (Lei 14.133/2021) e é CERTO."""
    item = next(i for i in parser.extrair_itens(pdf_bytes) if i["numero"] == 65)
    assert "licitação" in item["enunciado"].lower()
    assert item["gabarito"] == "CERTO"
    assert "14.133" in item["justificativa"]


def test_pdf_vazio_ou_invalido_devolve_lista_vazia():
    """Layout quebrado devolve vazio em vez de derrubar a coleta (CLAUDE.md 3)."""
    assert parser.extrair_itens(b"") == []
    assert parser.extrair_itens(b"nao sou um pdf") == []


FIXTURE_COLUNAS = Path(__file__).parent / "fixtures" / "cebraspe_duas_colunas.pdf"


@pytest.fixture
def pdf_duas_colunas():
    if not FIXTURE_COLUNAS.exists():
        pytest.skip("fixture cebraspe_duas_colunas.pdf ainda não baixada")
    return FIXTURE_COLUNAS.read_bytes()


def test_nao_perde_item_quando_uma_linha_atravessa_a_calha(pdf_duas_colunas):
    """Recorte fixo em largura/2 corta ao meio as linhas que cruzam a calha,
    embaralhando os blocos e fazendo o item perder a própria justificativa.

    Medido neste caderno (PCDF 2024, Conhecimentos Básicos): 50 marcadores de
    JUSTIFICATIVA no PDF. Com o recorte fixo saíam 49 itens — o 40 sumia.
    """
    itens = parser.extrair_itens(pdf_duas_colunas)
    numeros = sorted(i["numero"] for i in itens)
    faltando = sorted(set(range(numeros[0], numeros[-1] + 1)) - set(numeros))
    assert faltando == [], f"itens perdidos na extração: {faltando}"
    assert len(itens) == 50


FIXTURE_GABARITO = Path(__file__).parent / "fixtures" / "cebraspe_gabarito.pdf"


@pytest.fixture
def pdf_gabarito():
    if not FIXTURE_GABARITO.exists():
        pytest.skip("fixture cebraspe_gabarito.pdf ainda não baixada")
    return FIXTURE_GABARITO.read_bytes()


def test_extrai_o_mapa_de_gabaritos(pdf_gabarito):
    """Gabarito é tabela, não prosa em duas colunas.

    Medido na fixture (PRF 2021, gabarito definitivo dos itens 9 a 120):
    49 CERTO, 54 ERRADO e 9 anulados — 103 aproveitáveis.
    """
    mapa = parser.extrair_gabarito(pdf_gabarito)
    assert len(mapa) == 103
    assert set(mapa.values()) == {"CERTO", "ERRADO"}
    assert list(mapa.values()).count("CERTO") == 49
    assert list(mapa.values()).count("ERRADO") == 54


def test_item_anulado_fica_de_fora_do_mapa(pdf_gabarito):
    """`X` marca item anulado: não tem resposta certa, então não vira questão."""
    mapa = parser.extrair_gabarito(pdf_gabarito)
    for anulado in (39, 45, 67, 69, 76, 83, 89, 98, 99):
        assert anulado not in mapa


def test_gabarito_cobre_a_faixa_do_arquivo(pdf_gabarito):
    """Este arquivo cobre os itens 9 a 120; 1 a 8 vêm em outro arquivo."""
    mapa = parser.extrair_gabarito(pdf_gabarito)
    assert min(mapa) == 9
    assert max(mapa) == 120


def test_gabarito_de_pdf_invalido_devolve_dict_vazio():
    assert parser.extrair_gabarito(b"") == {}
    assert parser.extrair_gabarito(b"nao sou pdf") == {}


FIXTURE_CADERNO = Path(__file__).parent / "fixtures" / "cebraspe_caderno_simples.pdf"


@pytest.fixture
def pdf_caderno():
    if not FIXTURE_CADERNO.exists():
        pytest.skip("fixture cebraspe_caderno_simples.pdf ainda não baixada")
    return FIXTURE_CADERNO.read_bytes()


def test_extrai_enunciados_de_caderno_sem_gabarito(pdf_caderno):
    """A maioria dos concursos NÃO publica a versão `_COM_JUSTIFICATIVA`: publica
    o caderno (enunciado, sem resposta) e o gabarito (resposta, sem enunciado)
    em arquivos separados. O caderno comum não estava sendo lido, e a extração
    rendia 9.401 itens todos com enunciado vazio.

    Medido nesta fixture (ABIN 2017, Conhecimentos Específicos): 90 itens,
    numerados de 61 a 150.
    """
    itens = parser.extrair_enunciados(pdf_caderno)
    numeros = sorted(i["numero"] for i in itens)

    assert len(itens) == 90
    assert numeros[0] == 61
    assert numeros[-1] == 150
    assert sorted(set(range(61, 151))) == numeros, "houve item perdido ou repetido"


def test_enunciado_extraido_tem_texto_de_verdade(pdf_caderno):
    itens = {i["numero"]: i for i in parser.extrair_enunciados(pdf_caderno)}
    assert "Primeira República" in itens[61]["enunciado"]
    assert all(len(i["enunciado"]) > 20 for i in itens.values())


def test_caderno_sem_gabarito_nao_inventa_resposta(pdf_caderno):
    """Enunciado sem gabarito é meia questão; o gabarito vem do outro arquivo."""
    for item in parser.extrair_enunciados(pdf_caderno):
        assert item.get("gabarito") is None
