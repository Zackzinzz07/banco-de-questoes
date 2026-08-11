import db
from simulados import gerar_simulado


def questao_fake(i):
    return {
        "id_qc": f"Q{i}",
        "enunciado": f"Enunciado de teste número {i}: assinale a alternativa correta. Texto com < & > para escapar.",
        "alternativas": {"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D", "E": "Opção E"},
        "gabarito": "B" if i % 2 else None,
        "comentario": "Comentário da questão." if i == 1 else None,
        "materia": "Língua Portuguesa",
        "assunto": None, "banca": "Instituto Quadrix", "orgao": "SEDES/DF",
        "ano": 2026, "prova": None, "fonte": "qconcursos",
    }


def test_gera_pdf_e_marca_usadas(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    for i in range(3):
        db.salvar_questao(con, questao_fake(i))
    saida = tmp_path / "simulado.pdf"
    caminho = gerar_simulado.gerar("Língua Portuguesa", 3, saida, con=con)
    assert caminho == saida
    assert saida.exists() and saida.stat().st_size > 1000
    assert saida.read_bytes()[:5] == b"%PDF-"
    usadas = con.execute("SELECT COUNT(*) c FROM questoes WHERE usada_em_simulado=1").fetchone()["c"]
    assert usadas == 3


def test_banco_vazio_retorna_none(tmp_path, capsys):
    con = db.conectar(tmp_path / "t.db")
    assert gerar_simulado.gerar("SUAS", 5, tmp_path / "x.pdf", con=con) is None
    assert "Nenhuma questão" in capsys.readouterr().out
