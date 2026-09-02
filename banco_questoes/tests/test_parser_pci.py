"""Testes da extração de gabarito do PCI Concursos.

O PCI embute o gabarito da página inteira num JSON no próprio HTML
(`simGabaritos`), mapeando id da questão -> letra correta. Capturar isso na
coleta evita a fase separada de gabaritos (que no QConcursos depende de login
e de cota diária).
"""

from pathlib import Path

import pytest

from scrapers.pci import parser

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_pci.html"


@pytest.fixture
def html():
    if not FIXTURE.exists():
        pytest.skip("fixture pagina_pci.html ainda não capturada")
    return FIXTURE.read_text(encoding="utf-8")


def test_extrai_mapa_de_gabaritos(html):
    gabaritos = parser.extrair_gabaritos(html)
    assert len(gabaritos) >= 20
    assert gabaritos["2147610"] == "C"
    assert set(gabaritos.values()) <= set("ABCDE")


def test_extrair_gabaritos_sem_mapa_devolve_vazio():
    assert parser.extrair_gabaritos("<html><body>nada aqui</body></html>") == {}
    assert parser.extrair_gabaritos("") == {}


def test_extrair_gabaritos_ignora_json_corrompido():
    quebrado = "<script>var simGabaritos = {isso nao e json};</script>"
    assert parser.extrair_gabaritos(quebrado) == {}


def test_questoes_da_pagina_vem_com_gabarito(html):
    questoes = parser.extrair_questoes_pagina(html)
    assert questoes, "a fixture deveria ter questões"
    com_gabarito = [q for q in questoes if q.get("gabarito")]
    assert len(com_gabarito) >= len(questoes) // 2
    assert all(q["gabarito"] in set("ABCDE") for q in com_gabarito)


def test_gabarito_casa_com_a_questao_certa(html):
    questoes = {q["id_pci"]: q for q in parser.extrair_questoes_pagina(html)}
    gabaritos = parser.extrair_gabaritos(html)
    for id_pci, letra in gabaritos.items():
        if id_pci in questoes:
            assert questoes[id_pci]["gabarito"] == letra
