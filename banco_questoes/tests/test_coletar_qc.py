"""Testes do orquestrador da coleta no QConcursos."""

from pathlib import Path

import pytest

import coletar_qc
import db

FIXTURE = Path(__file__).parent / "fixtures" / "pagina_qc.html"


@pytest.fixture
def html():
    if not FIXTURE.exists():
        pytest.skip("fixture pagina_qc.html ainda não capturada")
    return FIXTURE.read_text(encoding="utf-8")


def _questao(id_qc, materia, gabarito=None):
    return {
        "id_qc": id_qc,
        "enunciado": f"Enunciado da {id_qc}?",
        "alternativas": {"A": "a", "B": "b"},
        "gabarito": gabarito,
        "materia": materia,
        "fonte": "qconcursos",
    }


def test_pendentes_por_materia_agrupa_e_tira_o_prefixo_q():
    """A fase de gabaritos casa o número do bloco na página (data-question-id,
    sem o "Q") com a questão do banco — por isso o prefixo sai aqui."""
    con = db.conectar()
    db.salvar_questao(con, _questao("Q111", "SUAS"))
    db.salvar_questao(con, _questao("Q222", "SUAS"))
    db.salvar_questao(con, _questao("Q333", "Direito Constitucional"))

    pendentes = coletar_qc._pendentes_por_materia(con)

    assert pendentes == {"SUAS": {"111", "222"}, "Direito Constitucional": {"333"}}
    con.close()


def test_pendentes_por_materia_ignora_quem_ja_tem_gabarito():
    con = db.conectar()
    db.salvar_questao(con, _questao("Q444", "SUAS", gabarito="A"))
    db.salvar_questao(con, _questao("Q555", "SUAS"))

    assert coletar_qc._pendentes_por_materia(con) == {"SUAS": {"555"}}
    con.close()


def test_pendentes_por_materia_vazio_quando_nao_ha_pendencia():
    con = db.conectar()
    db.salvar_questao(con, _questao("Q666", "SUAS", gabarito="B"))

    assert coletar_qc._pendentes_por_materia(con) == {}
    con.close()


def test_pendentes_por_materia_ignora_questao_sem_id_qc():
    """Sem id_qc não há como localizar o bloco na página para responder."""
    con = db.conectar()
    db.salvar_questao(con, _questao(None, "SUAS"))

    assert coletar_qc._pendentes_por_materia(con) == {}
    con.close()


class _AbaFalsa:
    """Navegador de mentira: devolve o HTML mapeado por página.

    Página sem mapeamento devolve HTML vazio — simula o erro 500 intermitente
    que o QConcursos devolveu (confirmado ao vivo: discipline_ids[]=213 deu 500
    numa sessão e voltou ao normal na seguinte).
    """

    def __init__(self, paginas):
        self.paginas = paginas
        self.visitadas = []

    def goto(self, url, **kwargs):
        numero = int(url.rsplit("page=", 1)[1])
        self.visitadas.append(numero)
        self._atual = self.paginas.get(numero, "<html></html>")

    def content(self):
        return self._atual


def test_pagina_vazia_isolada_nao_encerra_a_materia(html, monkeypatch):
    """Uma página vazia no meio era tratada como "acabou o conteúdo" e
    encerrava a matéria inteira. O QC tem 80 mil questões em Direito
    Administrativo e a coleta parava na página 20 por causa disso."""
    monkeypatch.setattr(coletar_qc.scraper_qc, "pausa", lambda: None)
    aba = _AbaFalsa({1: html, 3: html})  # a 2 vem vazia (erro transitório)

    con = db.conectar()
    coletar_qc.coletar_materia(aba, con, "SUAS", "https://exemplo/questoes?x=1")
    con.close()

    assert 3 in aba.visitadas, "parou na primeira página vazia em vez de tentar a seguinte"


def test_varias_paginas_vazias_seguidas_encerram_a_materia(html, monkeypatch):
    """Sem um limite, uma matéria realmente esgotada gastaria as 40 páginas."""
    monkeypatch.setattr(coletar_qc.scraper_qc, "pausa", lambda: None)
    aba = _AbaFalsa({1: html})  # da 2 em diante, tudo vazio

    con = db.conectar()
    coletar_qc.coletar_materia(aba, con, "SUAS", "https://exemplo/questoes?x=1")
    con.close()

    assert len(aba.visitadas) < 10, f"não parou: visitou {len(aba.visitadas)} páginas"
    assert len(aba.visitadas) >= 4, "parou cedo demais para tolerar erro transitório"


def test_coleta_vai_alem_das_materias_do_sedes():
    """O coletor iterava `edital.nomes_materias()` — as 8 do SEDES/DF. Nenhum
    dos outros 8 concursos configurados coletava questão nenhuma."""
    materias = dict(coletar_qc.materias_a_coletar())

    assert "Língua Portuguesa" in materias, "as originais precisam continuar"
    assert "Noções de Informática" in materias, "as novas precisam entrar"
    assert "Direito Penal Militar" in materias
    assert len(materias) > 8


def test_url_de_uma_materia_original_nao_mudou():
    """Mudar a URL faria o coletor recomeçar de outro conjunto de questões."""
    import edital

    materias = dict(coletar_qc.materias_a_coletar())
    antiga = edital.MATERIAS["Direito Administrativo"]["url_qc"]
    assert "discipline_ids%5B%5D=2" in materias["Direito Administrativo"]
    assert "discipline_ids%5B%5D=2" in antiga


def test_toda_materia_tem_url():
    """`Programas e Benefícios do DF` ficou meses com url vazia e era pulada
    silenciosamente em toda rodada."""
    for materia, url in coletar_qc.materias_a_coletar():
        assert url, f"{materia} sem url de busca"


def test_fase_de_gabaritos_cobre_as_mesmas_materias_da_coleta():
    """Se a coleta de enunciados vai além do SEDES mas a de gabaritos não, as
    questões das disciplinas novas ficam sem gabarito para sempre."""
    import inspect

    fonte = inspect.getsource(coletar_qc.coletar_gabaritos)
    assert "edital.nomes_materias" not in fonte, (
        "a fase de gabaritos ainda deriva as matérias do edital do SEDES"
    )
    assert "materias_a_coletar" in fonte
