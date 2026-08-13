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


def test_url_pagina():
    assert scraper_qc.url_pagina("https://x.com/q?a=1", 3) == "https://x.com/q?a=1&page=3"
    assert scraper_qc.url_pagina("https://x.com/q", 2) == "https://x.com/q?page=2"


def test_salvar_pagina_grava_no_banco(html, tmp_path):
    import db
    con = db.conectar(tmp_path / "t.db")
    novas = scraper_qc.salvar_pagina(html, con, "Língua Portuguesa")
    assert novas >= 5
    linha = con.execute("SELECT * FROM questoes LIMIT 1").fetchone()
    assert linha["fonte"] == "qconcursos"
    assert linha["materia"] == "Língua Portuguesa"
    # de novo: tudo duplicado
    assert scraper_qc.salvar_pagina(html, con, "Língua Portuguesa") == 0
