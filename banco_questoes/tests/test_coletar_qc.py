"""Testes do orquestrador da coleta no QConcursos."""

import coletar_qc
import db


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
