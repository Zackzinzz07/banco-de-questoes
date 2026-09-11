"""Monta um simulado com a FORMA de um edital, usando questões de qualquer banca.

É o "modo treino": mesmo número de questões e mesma proporção de matérias que a
prova real cobra, mas o conteúdo vem do acervo inteiro — prefeituras, conselhos,
outras bancas. Serve para treinar a distribuição da prova antes de ela existir.

Três coisas que este módulo NÃO faz, e cada uma tem motivo:

  não completa com questão de outra matéria — foi assim que um simulado do PMDF
  saiu com Lei Municipal de Estância/SE sob "Legislação Específica da PMDF";

  não inventa correspondência de nome — quem traduz é `taxonomia`, que erra
  para excluir;

  não esconde o buraco — devolve o que faltou, para quem chamou avisar.
"""

import pytest

import db
from simulados import por_edital


def _questao(n, materia):
    return {
        "id_qc": f"QED{n}",
        "enunciado": f"Enunciado número {n} de {materia}?",
        "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "gabarito": "A",
        "materia": materia,
        "fonte": "pci",
    }


@pytest.fixture
def banco_com_questoes():
    con = db.conectar()
    for materia in ("Língua Portuguesa", "Direito Administrativo", "Matemática"):
        for n in range(40):
            db.salvar_questao(con, _questao(f"{materia[:3]}{n}", materia))
    yield con
    con.close()


def test_distribui_conforme_os_pesos_do_edital(banco_com_questoes):
    pesos = {"Língua Portuguesa": 10, "Direito Administrativo": 10}
    montado = por_edital.montar(banco_com_questoes, pesos, quantidade=20)

    assert len(montado.questoes) == 20
    por_materia = {}
    for q in montado.questoes:
        por_materia[q["materia"]] = por_materia.get(q["materia"], 0) + 1
    assert por_materia == {"Língua Portuguesa": 10, "Direito Administrativo": 10}


def test_traduz_o_nome_do_edital_para_o_do_banco(banco_com_questoes):
    """O edital escreve "Noções de"; o banco não."""
    montado = por_edital.montar(banco_com_questoes, {"Noções de Direito Administrativo": 5}, 5)
    assert len(montado.questoes) == 5
    assert all(q["materia"] == "Direito Administrativo" for q in montado.questoes)


def test_materia_composta_divide_a_cota(banco_com_questoes):
    """ "Matemática e Língua Portuguesa" vale 10: 5 de cada."""
    montado = por_edital.montar(banco_com_questoes, {"Matemática e Língua Portuguesa": 10}, 10)
    materias = {q["materia"] for q in montado.questoes}
    assert materias == {"Matemática", "Língua Portuguesa"}
    assert len(montado.questoes) == 10


def test_materia_sem_correspondencia_vira_lacuna_declarada(banco_com_questoes):
    """Nunca preenche com outra matéria: devolve menos e diz o que faltou."""
    pesos = {"Língua Portuguesa": 5, "Criminologia Aplicada": 5}
    montado = por_edital.montar(banco_com_questoes, pesos, quantidade=10)

    assert len(montado.questoes) == 5
    assert all(q["materia"] == "Língua Portuguesa" for q in montado.questoes)
    assert montado.lacunas == {"Criminologia Aplicada": 5}


def test_materia_com_acervo_insuficiente_tambem_vira_lacuna(banco_com_questoes):
    """O banco tem 40 de Matemática; pedir 60 deixa 20 faltando."""
    montado = por_edital.montar(banco_com_questoes, {"Matemática": 60}, quantidade=60)
    assert len(montado.questoes) == 40
    assert montado.lacunas == {"Matemática": 20}


def test_sem_lacuna_o_relatorio_vem_vazio(banco_com_questoes):
    montado = por_edital.montar(banco_com_questoes, {"Matemática": 10}, quantidade=10)
    assert montado.lacunas == {}
    assert montado.completo is True


def test_com_lacuna_o_simulado_se_declara_incompleto(banco_com_questoes):
    montado = por_edital.montar(banco_com_questoes, {"Criminologia Aplicada": 5}, quantidade=5)
    assert montado.completo is False


def test_nao_repete_questao_no_mesmo_simulado(banco_com_questoes):
    montado = por_edital.montar(banco_com_questoes, {"Matemática": 30}, quantidade=30)
    ids = [q["id"] for q in montado.questoes]
    assert len(ids) == len(set(ids))


def _questao_certo_errado(n, materia):
    return {
        "id_qc": f"QCE{n}",
        "enunciado": f"Certo ou errado, questão {n} de {materia}?",
        "alternativas": {"C": "Certo", "E": "Errado"},
        "gabarito": "C",
        "materia": materia,
        "fonte": "pci",
    }


def test_normalizar_formato_aceita_o_valor_do_yaml_do_edital():
    assert por_edital._normalizar_formato("Certo_Errado") == "certo_errado"
    assert por_edital._normalizar_formato("Multipla_Escolha") == "multipla_escolha"


def test_normalizar_formato_desconhecido_vira_none():
    """Filtrar por lixo esvaziaria o sorteio inteiro — melhor não filtrar."""
    assert por_edital._normalizar_formato("pdf") is None
    assert por_edital._normalizar_formato(None) is None


def test_formato_filtra_e_declara_lacuna_sem_completar_com_outro_formato(banco_com_questoes):
    """Regra de ouro: sem C/E suficiente, vira lacuna — nunca é completado com ME."""
    con = banco_com_questoes
    for n in range(3):
        db.salvar_questao(con, _questao_certo_errado(n, "Língua Portuguesa"))

    montado = por_edital.montar(con, {"Língua Portuguesa": 5}, quantidade=5, formato="Certo_Errado")

    assert len(montado.questoes) == 3
    assert all(q["formato"] == "certo_errado" for q in montado.questoes)
    assert montado.lacunas == {"Língua Portuguesa": 2}


def test_formato_multipla_escolha_nao_pega_questao_certo_errado(banco_com_questoes):
    con = banco_com_questoes
    db.salvar_questao(con, _questao_certo_errado(99, "Matemática"))

    montado = por_edital.montar(con, {"Matemática": 5}, quantidade=5, formato="Multipla_Escolha")
    assert all(q["formato"] == "multipla_escolha" for q in montado.questoes)


def _questao_portugues_categoria(n, categoria):
    return {
        "id_qc": f"QPT{n}",
        "enunciado": f"Questão {n} de {categoria}?",
        "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d"},
        "gabarito": "A",
        "materia": "Língua Portuguesa",
        "categoria": categoria,
        "fonte": "pci",
    }


def test_ordena_portugues_pela_precedencia_pedagogica(banco_com_questoes):
    """A prova real começa por interpretação, não por gramática (achado do
    relatório de bug do simulado do PMDF)."""
    con = banco_com_questoes
    con.execute("DELETE FROM questoes WHERE materia='Língua Portuguesa'")
    db.salvar_questao(con, _questao_portugues_categoria(1, "Sintaxe"))
    db.salvar_questao(con, _questao_portugues_categoria(2, "Interpretação de Textos"))
    db.salvar_questao(con, _questao_portugues_categoria(3, "Morfologia"))

    montado = por_edital.montar(con, {"Língua Portuguesa": 3}, quantidade=3)
    categorias = [q["categoria"] for q in montado.questoes]
    assert categorias == ["Interpretação de Textos", "Morfologia", "Sintaxe"]


def test_agrupa_texto_associado_no_simulado_final(banco_com_questoes):
    con = banco_com_questoes
    con.execute("DELETE FROM questoes WHERE materia='Língua Portuguesa'")
    q1 = _questao_portugues_categoria(1, "Interpretação de Textos")
    q1["texto_associado"] = "Texto Base"
    q2 = _questao_portugues_categoria(2, "Interpretação de Textos")
    q3 = _questao_portugues_categoria(3, "Interpretação de Textos")
    q3["texto_associado"] = "Texto Base"
    for q in (q1, q2, q3):
        db.salvar_questao(con, q)

    montado = por_edital.montar(con, {"Língua Portuguesa": 3}, quantidade=3)
    textos = [q["texto_associado"] for q in montado.questoes]
    idx_base = [i for i, t in enumerate(textos) if t == "Texto Base"]
    assert idx_base == [idx_base[0], idx_base[0] + 1], "as duas do mesmo texto não ficaram juntas"
