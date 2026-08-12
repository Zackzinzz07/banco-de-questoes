import db
import coletor_quadrix as cq

TEXTO_PROVA = """
CONHECIMENTOS BÁSICOS
LÍNGUA PORTUGUESA

QUESTÃO 1
Assinale a alternativa correta quanto à crase.
(A) Fui à feira.
(B) Fui a feira.
(C) Fui à feiras.
(D) Fui a à feira.
(E) Nenhuma.

QUESTÃO 2
Enunciado sem alternativas legíveis para o parser.

NOÇÕES DE DIREITO ADMINISTRATIVO

QUESTÃO 3
Sobre atos administrativos, julgue os itens e assinale
a alternativa correta.
(A) Item um.
(B) Item dois.
(C) Item três.
(D) Item quatro.
(E) Item cinco.
"""


def test_extrai_questoes_com_materia():
    questoes, puladas = cq.extrair_questoes_do_texto(TEXTO_PROVA)
    assert [q["numero"] for q in questoes] == [1, 3]
    assert puladas == [2]
    assert questoes[0]["materia"] == "Língua Portuguesa"
    assert questoes[1]["materia"] == "Direito Administrativo"
    assert questoes[0]["alternativas"]["A"] == "Fui à feira."
    assert len(questoes[1]["alternativas"]) == 5
    assert "julgue os itens e assinale a alternativa" in questoes[1]["enunciado"]


def test_gabarito_de_tabelas():
    tabelas = [
        [["1", "2", "3"], ["A", "C", "E"]],
        [["4", "5"], ["B", None]],
    ]
    gab = cq.extrair_gabarito_de_tabelas(tabelas)
    assert gab == {1: "A", 2: "C", 3: "E", 4: "B"}


def test_casar_gabarito():
    questoes = [{"numero": 1}, {"numero": 3}]
    cq.casar_gabarito(questoes, {1: "A", 2: "C"})
    assert questoes[0]["gabarito"] == "A"
    assert questoes[1]["gabarito"] is None


def test_gabarito_rejeita_multiplos_caracteres():
    """Garbled merged cells like BC ou CDE não devem ser aceitos como gabarito."""
    tabelas = [
        [["1", "2", "3", "4"], ["A", "BC", "E", "CDE"]],
    ]
    gab = cq.extrair_gabarito_de_tabelas(tabelas)
    assert gab == {1: "A", 3: "E"}  # 2 e 4 foram rejeitados
    assert 2 not in gab
    assert 4 not in gab


def test_secoes_nao_confundem_palavras_lowercase():
    """Palavras lowercase no enunciado (e.g. 'suas') não criam seção falsa SUAS."""
    texto_com_lowercase = """
LÍNGUA PORTUGUESA

QUESTÃO 1
Verifique suas respostas.
(A) Opção A.
(B) Opção B.

QUESTÃO 2
Sobre benefícios sociais.
(A) Item um.
(B) Item dois.
"""
    questoes, puladas = cq.extrair_questoes_do_texto(texto_com_lowercase)
    assert len(questoes) == 2
    assert questoes[0]["numero"] == 1
    assert questoes[1]["numero"] == 2
    assert questoes[0]["materia"] == "Língua Portuguesa"
    assert questoes[1]["materia"] == "Língua Portuguesa"  # Não mudou para SUAS


def test_processar_prova_texto(tmp_path, monkeypatch):
    con = db.conectar(tmp_path / "t.db")
    monkeypatch.setattr(cq, "_texto_do_pdf", lambda caminho: cq_texto_fake(caminho))
    monkeypatch.setattr(cq, "_tabelas_do_pdf",
                        lambda caminho: [[["1", "3"], ["A", "B"]]])
    resultado = cq.processar_prova("prova.pdf", "gab.pdf", con,
                                   {"banca": "Instituto Quadrix", "orgao": "CRT-4",
                                    "ano": 2024, "prova": "Assistente Administrativo"})
    assert resultado["salvas"] == 2
    assert resultado["puladas"] == [2]
    linha = con.execute("SELECT * FROM questoes WHERE materia='Língua Portuguesa'").fetchone()
    assert linha["gabarito"] == "A"
    assert linha["fonte"] == "quadrix_pdf"
    assert linha["id_qc"] is None
    # rodar de novo: tudo duplicado
    resultado2 = cq.processar_prova("prova.pdf", "gab.pdf", con, {"ano": 2024})
    assert resultado2["salvas"] == 0
    assert resultado2["duplicadas"] == 2


def cq_texto_fake(caminho):
    return TEXTO_PROVA


def test_baixar_usa_cache(tmp_path, monkeypatch):
    destino = tmp_path / "prova.pdf"
    destino.write_bytes(b"%PDF-cache")

    def explode(*a, **kw):
        raise AssertionError("não deveria baixar de novo")

    monkeypatch.setattr(cq.requests, "get", explode)
    assert cq.baixar("http://exemplo/prova.pdf", destino) == destino
