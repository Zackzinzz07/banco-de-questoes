"""Traduz o nome de matéria do edital para os nomes que existem no banco.

O edital e as fontes de questão usam vocabulários diferentes, e isso travava o
multi-concurso inteiro. Medido no edital do PMDF Soldado: das 10 matérias
pedidas, 9 devolviam ZERO no banco — não por falta de conteúdo, mas porque o
edital escreve "Noções de Direito Administrativo" e o banco guarda "Direito
Administrativo". Um simulado de 120 questões saía com 15.

Quatro tipos de divergência, cada um com mecanismo próprio:
  prefixo     "Noções de Direito Administrativo" -> "Direito Administrativo"
  decomposição "Matemática e Raciocínio Lógico"  -> as duas, separadas
  fusão        (o banco junta o que o edital separa)
  bloco        "Conhecimentos Básicos" não é matéria, é rótulo de prova

O guardrail é o que impede o remédio de virar veneno: "Direito Penal Militar"
NÃO pode casar com "Direito Penal". São ramos distintos, com legislação
própria, e o edital do PMDF cobra os dois separadamente.
"""

import taxonomia


def test_remove_prefixo_de_nocoes():
    assert taxonomia.normalizar("Noções de Direito Administrativo") == "direito administrativo"


def test_remove_outros_prefixos_de_edital():
    for texto in ("Fundamentos de Estatística", "Princípios de Estatística"):
        assert taxonomia.normalizar(texto) == "estatistica"


def test_ignora_acento_caixa_e_pontuacao():
    assert taxonomia.normalizar("LÍNGUA PORTUGUESA") == "lingua portuguesa"
    assert taxonomia.normalizar("Direito Administrativo (Bloco III)") == "direito administrativo"


def test_resolve_pelo_nome_exato():
    disponiveis = ["Direito Administrativo", "Matemática"]
    assert taxonomia.resolver("Direito Administrativo", disponiveis) == ["Direito Administrativo"]


def test_resolve_apesar_do_prefixo():
    disponiveis = ["Direito Administrativo"]
    assert taxonomia.resolver("Noções de Direito Administrativo", disponiveis) == [
        "Direito Administrativo"
    ]


def test_decompoe_materia_composta():
    """O edital junta o que o banco separa; a cota se divide entre as duas."""
    disponiveis = ["Matemática", "Raciocínio Lógico"]
    assert taxonomia.resolver("Matemática e Raciocínio Lógico", disponiveis) == [
        "Matemática",
        "Raciocínio Lógico",
    ]


def test_decompoe_repetindo_o_nucleo_omitido():
    """ "Direito Penal e Processual Penal" quer dizer Direito Penal E Direito
    Processual Penal — o "Direito" do segundo fica subentendido."""
    disponiveis = ["Direito Penal", "Direito Processual Penal"]
    assert taxonomia.resolver("Direito Penal e Processual Penal", disponiveis) == [
        "Direito Penal",
        "Direito Processual Penal",
    ]


def test_guardrail_impede_militar_de_virar_comum():
    """O erro que corrói a confiança: questão de Direito Penal Militar num
    simulado de Direito Penal, ou vice-versa."""
    assert taxonomia.resolver("Direito Penal Militar", ["Direito Penal"]) == []
    assert taxonomia.resolver("Direito Penal", ["Direito Penal Militar"]) == []


def test_guardrail_vale_para_processual():
    assert taxonomia.resolver("Direito Processual Penal", ["Direito Penal"]) == []


def test_guardrail_nao_atrapalha_quando_os_dois_tem_o_termo():
    disponiveis = ["Direito Penal Militar"]
    assert taxonomia.resolver("Noções de Direito Penal Militar", disponiveis) == [
        "Direito Penal Militar"
    ]


def test_bloco_de_prova_nao_e_materia():
    """ "Conhecimentos Básicos" agrupa matérias; casar seria inventar."""
    for bloco in ("Conhecimentos Básicos", "Conhecimentos Específicos", "Conhecimentos Gerais"):
        assert taxonomia.resolver(bloco, ["Língua Portuguesa", "Matemática"]) == []


def test_sem_correspondencia_devolve_vazio():
    """Erra para EXCLUIR: melhor simulado menor com aviso que questão errada."""
    assert taxonomia.resolver("Criminologia Aplicada", ["Língua Portuguesa"]) == []


def test_nao_casa_por_conter_a_palavra():
    """ "Direito" não pode arrastar todas as matérias que começam com Direito."""
    disponiveis = ["Direito Administrativo", "Direito Penal", "Direito Constitucional"]
    assert taxonomia.resolver("Direito", disponiveis) == []
