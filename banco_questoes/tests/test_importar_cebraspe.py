"""Testes da vinculação de itens arquivados da Cebraspe à tabela `questoes`."""

import db
from scripts import importar_cebraspe


def _item(numero, enunciado=None, gabarito="CERTO", concurso="prf_21", arquivo="a.pdf"):
    # Enunciado distinto por padrão: dois itens com texto igual colidiriam no
    # dedupe por content_hash de db.salvar_questao, mascarando o teste.
    return {
        "numero": numero,
        "enunciado": enunciado or f"Julgue o item {numero}.",
        "gabarito": gabarito,
        "justificativa": "Justificativa oficial.",
        "concurso": concurso,
        "arquivo": arquivo,
    }


def test_calcular_faixas_a_partir_dos_pesos_do_edital():
    pesos = {"Língua Portuguesa": 15, "Língua Inglesa": 5, "Matemática": 10}
    assert importar_cebraspe.calcular_faixas(pesos) == [
        (1, 15, "Língua Portuguesa"),
        (16, 20, "Língua Inglesa"),
        (21, 30, "Matemática"),
    ]


def test_resolver_materia_acha_a_faixa_certa():
    faixas = importar_cebraspe.calcular_faixas({"A": 10, "B": 5})
    assert importar_cebraspe.resolver_materia(1, faixas) == "A"
    assert importar_cebraspe.resolver_materia(10, faixas) == "A"
    assert importar_cebraspe.resolver_materia(11, faixas) == "B"
    assert importar_cebraspe.resolver_materia(15, faixas) == "B"


def test_resolver_materia_fora_de_toda_faixa_devolve_none():
    """Numeração que não bate com o edital não vira palpite de matéria."""
    faixas = importar_cebraspe.calcular_faixas({"A": 10})
    assert importar_cebraspe.resolver_materia(0, faixas) is None
    assert importar_cebraspe.resolver_materia(11, faixas) is None


def test_importar_usa_a_faixa_do_edital_para_resolver_a_materia():
    """prf.yaml tem 1 cargo só: item 5 é Português, item 60 é Trânsito."""
    con = db.conectar()
    itens = [_item(5), _item(60, gabarito="ERRADO")]

    contagem = importar_cebraspe.importar(con, itens, "prf")

    assert contagem == {"salvas": 2, "duplicadas": 0, "sem_materia": 0}
    linha5 = con.execute(
        "SELECT * FROM questoes WHERE id_qc = 'cebraspe_prf_21_a.pdf_5'"
    ).fetchone()
    assert linha5["materia"] == "Língua Portuguesa (Bloco I)"
    assert linha5["gabarito"] == "C"
    assert linha5["formato"] == "certo_errado"
    assert linha5["fonte"] == "cebraspe"
    assert linha5["banca"] == "Cebraspe"
    assert linha5["orgao"] == "Polícia Rodoviária Federal"

    linha60 = con.execute(
        "SELECT * FROM questoes WHERE id_qc = 'cebraspe_prf_21_a.pdf_60'"
    ).fetchone()
    assert linha60["materia"] == "Legislação Especial de Trânsito - CTB e CONTRAN (Bloco II)"
    assert linha60["gabarito"] == "E"


def test_importar_nao_grava_item_fora_da_faixa_do_edital():
    """PRF tem 120 itens; item 121 não existe no quadro de provas."""
    con = db.conectar()
    contagem = importar_cebraspe.importar(con, [_item(121)], "prf")
    assert contagem == {"salvas": 0, "duplicadas": 0, "sem_materia": 1}
    assert con.execute("SELECT COUNT(*) c FROM questoes").fetchone()["c"] == 0


def test_importar_e_idempotente():
    con = db.conectar()
    itens = [_item(5)]
    importar_cebraspe.importar(con, itens, "prf")
    contagem = importar_cebraspe.importar(con, itens, "prf")
    assert contagem == {"salvas": 0, "duplicadas": 1, "sem_materia": 0}


def test_importar_exige_cargo_quando_edital_tem_mais_de_um():
    """PCDF tem 4 cargos; cada um com numeração própria — não dá pra adivinhar."""
    con = db.conectar()
    try:
        importar_cebraspe.importar(con, [_item(5)], "pcdf")
        assert False, "deveria ter levantado ValueError"
    except ValueError as erro:
        assert "cargo" in str(erro).lower()


def test_importar_aceita_cargo_explicito_em_edital_multi_cargo():
    con = db.conectar()
    itens = [_item(10, concurso="pc_df_24", arquivo="perito.pdf")]
    contagem = importar_cebraspe.importar(con, itens, "pcdf", cargo="Perito Criminal")
    assert contagem == {"salvas": 1, "duplicadas": 0, "sem_materia": 0}
    linha = con.execute("SELECT materia FROM questoes").fetchone()
    assert linha["materia"] == "Conhecimentos Básicos"


def test_importar_edital_desconhecido_levanta_erro():
    con = db.conectar()
    try:
        importar_cebraspe.importar(con, [_item(1)], "concurso-que-nao-existe")
        assert False, "deveria ter levantado ValueError"
    except ValueError as erro:
        assert "não encontrado" in str(erro)


def test_importar_gabarito_ausente_grava_questao_mesmo_assim():
    """Sem gabarito não é motivo de exclusão (existe fluxo pra completar
    depois, ver db.sem_gabarito) — só matéria incerta exclui."""
    con = db.conectar()
    contagem = importar_cebraspe.importar(con, [_item(5, gabarito=None)], "prf")
    assert contagem["salvas"] == 1
    linha = con.execute("SELECT gabarito FROM questoes").fetchone()
    assert linha["gabarito"] is None
