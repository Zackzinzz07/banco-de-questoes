from pathlib import Path

import pytest

import scraper_qc

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_qc.html"


@pytest.fixture
def html():
    if not FIXTURE.exists():
        pytest.skip("fixture pagina_qc.html ainda não capturada")
    return FIXTURE.read_text(encoding="utf-8")


def test_extrai_blocos_da_pagina_real(html):
    blocos = scraper_qc.extrair_blocos(html)
    assert len(blocos) >= 5  # uma página de busca tem vários resultados
    primeiro = blocos[0]
    assert primeiro["id_qc"].startswith("Q")
    assert len(primeiro["enunciado"]) > 20
    assert len(primeiro["alternativas"]) >= 2
    letras = set(primeiro["alternativas"])
    assert letras <= set("ABCDE") or letras == {"C", "E"}
    assert primeiro["ano"] is None or isinstance(primeiro["ano"], int)
