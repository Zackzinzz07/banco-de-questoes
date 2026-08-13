from pathlib import Path

import pytest

import scraper_qc

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_qc.html"
FIXTURE_RESPONDIDA = Path(__file__).parent / "fixtures" / "questao_respondida.html"


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


def test_atingiu_limite_pelo_atributo_do_botao():
    # Achado de calibração ao vivo: a cota diária esgotada é sinalizada
    # primeiro no próprio botão "Responder" (data-limit-reached="true").
    html_limite = (
        '<button type="button" class="js-answer-btn btn btn-primary" '
        'data-question-id="4228008" data-discipline="Português" '
        'data-permissions="confirmed_account,account" '
        'data-limit-feedback="resolveQuestionLimit" data-limit-reached="true" '
        'aria-disabled="false">Responder</button>'
    )
    assert scraper_qc.atingiu_limite(html_limite)


def test_atingiu_limite_pelo_modal():
    html_modal = (
        '<div id="js-questions-limit-modal">'
        'Você atingiu o seu limite diário de questões gratuitas.</div>'
    )
    assert scraper_qc.atingiu_limite(html_modal)


def test_nao_atingiu_limite():
    html_normal = (
        '<button type="button" class="js-answer-btn btn btn-primary" '
        'data-question-id="4228008" data-discipline="Português" '
        'data-permissions="confirmed_account,account" '
        'data-limit-feedback="resolveQuestionLimit" data-limit-reached="false" '
        'aria-disabled="false">Responder</button>'
    )
    assert not scraper_qc.atingiu_limite(html_normal)
    assert not scraper_qc.atingiu_limite("<div>página normal</div>")


def test_extrair_resposta_do_bloco_quando_errou():
    # Achado crítico de calibração: js-question-right-answer só vem
    # preenchido quando a alternativa marcada estava ERRADA — nesse caso a
    # letra ali dentro é o gabarito oficial, mesmo que a marcada tenha sido
    # outra ("A" aqui, mas o gabarito real é "B").
    bloco_html = (
        '<div class="js-response-wrong q-inline-answer q-wrong feedback-redesign" role="alert">'
        '<div class="q-answer-feedback"><p class="q-answer-feedback-item">'
        'Incorreta. Gabarito oficial da banca: '
        '<span class="hide-question-answer-template">'
        '<b><span class="js-question-right-answer" role="text" aria-label="B">B</span></b>'
        '</span></p></div></div>'
    )
    gabarito, comentario = scraper_qc.extrair_resposta_do_bloco(bloco_html, "A")
    assert gabarito == "B"
    assert comentario is None


def test_extrair_resposta_do_bloco_quando_acertou():
    # Quando a marcada é a certa, js-question-right-answer fica vazio; o
    # gabarito é a própria letra marcada, sinalizado pelo feedback de acerto.
    bloco_html = (
        '<div class="js-response-correct q-inline-answer q-correct feedback-redesign" role="alert">'
        '<div class="q-answer-feedback"><p class="q-answer-feedback-item">'
        'Parabéns! Você acertou!</p></div></div>'
    )
    gabarito, comentario = scraper_qc.extrair_resposta_do_bloco(bloco_html, "b")
    assert gabarito == "B"
    assert comentario is None


def test_extrair_resposta_do_bloco_sem_nada():
    assert scraper_qc.extrair_resposta_do_bloco("<div></div>", "A") == (None, None)


def test_extrai_texto_associado_e_imagens():
    if not FIXTURE_RESPONDIDA.exists():
        pytest.skip("fixture questao_respondida.html ausente")
    blocos = scraper_qc.extrair_blocos(FIXTURE_RESPONDIDA.read_text(encoding="utf-8"))
    assert blocos, "fixture deveria ter questões"
    com_texto = [b for b in blocos if b["texto_associado"]]
    com_imagem = [b for b in blocos if b["imagens"]]
    assert com_texto, "a fixture tem questões com texto-base"
    assert com_imagem, "a fixture tem questões com imagem"
    assert all(u.startswith("http") for b in com_imagem for u in b["imagens"])
