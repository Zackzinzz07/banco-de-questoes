import pytest
import db


def questao_exemplo(**extras):
    q = {
        "id_qc": "Q1234567",
        "enunciado": "Qual é a capital do Brasil?",
        "alternativas": {"A": "Brasília", "B": "Goiânia", "C": "Rio", "D": "SP", "E": "BH"},
        "gabarito": "A",
        "comentario": None,
        "materia": "Língua Portuguesa",
        "assunto": "Interpretação de textos",
        "banca": "Instituto Quadrix",
        "orgao": "SEDES/DF",
        "ano": 2026,
        "prova": "Técnico Administrativo",
        "fonte": "qconcursos",
    }
    q.update(extras)
    return q


def test_salvar_e_ler():
    con = db.conectar()
    assert db.salvar_questao(con, questao_exemplo()) is True
    linha = con.execute("SELECT * FROM questoes").fetchone()
    assert linha["id_qc"] == "Q1234567"
    assert linha["materia"] == "Língua Portuguesa"
    assert linha["usada_em_simulado"] == 0


def test_dedupe_por_id_qc():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    assert db.salvar_questao(con, questao_exemplo(enunciado="Outro texto")) is False


def test_dedupe_por_hash_enunciado():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    repetida = questao_exemplo(id_qc=None, enunciado="  qual  é a CAPITAL do Brasil? ")
    assert db.salvar_questao(con, repetida) is False


def test_duas_questoes_sem_id_qc_nao_conflitam():
    con = db.conectar()
    assert db.salvar_questao(con, questao_exemplo(id_qc=None)) is True
    assert db.salvar_questao(con, questao_exemplo(id_qc=None, enunciado="Texto diferente.")) is True


def test_normalizar_enunciado():
    assert db.normalizar_enunciado("  Olá   MUNDO \n ") == "olá mundo"


def test_fonte_invalida_raises_error():
    con = db.conectar()
    with pytest.raises(ValueError, match="fonte inválida"):
        db.salvar_questao(con, questao_exemplo(fonte="outra"))


def test_sorteio_sem_repeticao():
    con = db.conectar()
    for i in range(5):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    sorteadas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    assert len(sorteadas) == 3
    assert isinstance(sorteadas[0]["alternativas"], dict)
    db.marcar_usadas(con, [q["id"] for q in sorteadas])
    restantes = db.sortear_questoes(con, "Língua Portuguesa", 2)
    ids_novos = {q["id"] for q in restantes}
    assert ids_novos.isdisjoint({q["id"] for q in sorteadas})


def test_sorteio_completa_com_repetidas(capsys):
    con = db.conectar()
    for i in range(3):
        db.salvar_questao(con, questao_exemplo(id_qc=f"Q{i}", enunciado=f"Enunciado {i}?"))
    todas = db.sortear_questoes(con, "Língua Portuguesa", 3)
    db.marcar_usadas(con, [q["id"] for q in todas])
    de_novo = db.sortear_questoes(con, "Língua Portuguesa", 2)
    assert len(de_novo) == 2
    assert "repetidas" in capsys.readouterr().out


def test_zerar_usadas():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo())
    q = db.sortear_questoes(con, "Língua Portuguesa", 1)
    db.marcar_usadas(con, [q[0]["id"]])
    db.zerar_usadas(con)
    assert con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"] == 0


def test_progresso():
    con = db.conectar()
    assert db.obter_progresso(con, "qconcursos", "Direito Administrativo") == 0
    db.salvar_progresso(con, "qconcursos", "Direito Administrativo", 7)
    db.salvar_progresso(con, "qconcursos", "Direito Administrativo", 8)
    assert db.obter_progresso(con, "qconcursos", "Direito Administrativo") == 8


def test_salva_e_le_texto_associado():
    con = db.conectar()
    q = questao_exemplo(texto_associado="Poema base da questão.",
                        imagens=["https://x/a.png"])
    db.salvar_questao(con, q)
    lida = db.sortear_questoes(con, "Língua Portuguesa", 1)[0]
    assert lida["texto_associado"] == "Poema base da questão."
    assert lida["imagens"] == ["https://x/a.png"]


def test_completar_texto_associado_preenche_so_quando_vazio():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QT1"))
    assert db.completar_texto_associado(con, "QT1", "Texto novo.", ["u1"]) is True
    assert db.completar_texto_associado(con, "QT1", "Outro texto.", []) is False
    linha = con.execute("SELECT texto_associado FROM questoes WHERE id_qc='QT1'").fetchone()
    assert linha["texto_associado"] == "Texto novo."


def test_sem_gabarito_e_atualizar():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="Q1", gabarito=None, enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="Q2", gabarito="B", enunciado="Dois?"))
    db.salvar_questao(con, questao_exemplo(id_qc=None, gabarito=None, enunciado="Três?"))
    pendentes = db.sem_gabarito(con)
    assert [p["id_qc"] for p in pendentes] == ["Q1"]
    db.atualizar_gabarito(con, "Q1", "C", "Comentário do professor.")
    linha = con.execute("SELECT gabarito, comentario FROM questoes WHERE id_qc='Q1'").fetchone()
    assert (linha["gabarito"], linha["comentario"]) == ("C", "Comentário do professor.")


def test_estatisticas():
    con = db.conectar()
    db.salvar_questao(con, questao_exemplo(id_qc="QA", enunciado="Um?"))
    db.salvar_questao(con, questao_exemplo(id_qc="QB", enunciado="Dois?", gabarito=None))
    db.salvar_questao(con, questao_exemplo(id_qc="QC1", enunciado="Três?",
                                           materia="SUAS"))
    usada = db.sortear_questoes(con, "SUAS", 1)
    db.marcar_usadas(con, [usada[0]["id"]])
    est = db.estatisticas(con)
    assert est["Língua Portuguesa"] == {"total": 2, "ineditas": 2, "usadas": 0,
                                        "sem_gabarito": 1}
    assert est["SUAS"] == {"total": 1, "ineditas": 0, "usadas": 1, "sem_gabarito": 0}
