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
