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


def test_resolve_sinonimo_lingua_inglesa():
    """O edital do PMDF pede "Língua Inglesa"; o banco guarda "Inglês" — mesma
    matéria, palavras diferentes. Achado real: virava lacuna de 5 questões."""
    assert taxonomia.resolver("Língua Inglesa", ["Inglês"]) == ["Inglês"]


def test_resolve_sinonimo_portugues_sem_lingua():
    """Banco do Brasil, Correios, INSS e Receita Federal escrevem só
    "Português" no edital; o banco guarda "Língua Portuguesa". Achado real:
    zerava a matéria de maior peso em 4 dos 9 editais cadastrados."""
    assert taxonomia.resolver("Português", ["Língua Portuguesa"]) == ["Língua Portuguesa"]


def test_resolve_sigla_de_transito_do_edital_prf():
    """O edital do PRF nomeia a matéria pelas siglas da legislação (CTB,
    CONTRAN) em vez do nome que o banco guarda. Achado real: 30 das 120
    questões do PRF (25% da prova) viravam lacuna."""
    materia = "Legislação Especial de Trânsito - CTB e CONTRAN (Bloco II)"
    assert taxonomia.resolver(materia, ["Legislação de Trânsito"]) == ["Legislação de Trânsito"]


def test_resolve_lingua_estrangeira_ingles_ou_espanhol():
    """PRF pede "Inglês ou Espanhol"; o acervo só cataloga "Inglês"."""
    materia = "Língua Estrangeira - Inglês ou Espanhol (Bloco I)"
    assert taxonomia.resolver(materia, ["Inglês"]) == ["Inglês"]


def test_decompoe_com_adjetivo_no_lugar_do_substantivo():
    """ "Raciocínio Lógico e Matemático" concorda no masculino com
    "Raciocínio"; o banco guarda o substantivo "Matemática". Sem a
    equivalência, a cota inteira ia parar em Raciocínio Lógico e a
    Matemática nunca era sorteada (achado real do edital do PMDF)."""
    disponiveis = ["Raciocínio Lógico", "Matemática"]
    assert taxonomia.resolver("Raciocínio Lógico e Matemático", disponiveis) == [
        "Matemática",
        "Raciocínio Lógico",
    ]


def test_nao_casa_por_conter_a_palavra():
    """ "Direito" não pode arrastar todas as matérias que começam com Direito."""
    disponiveis = ["Direito Administrativo", "Direito Penal", "Direito Constitucional"]
    assert taxonomia.resolver("Direito", disponiveis) == []


def _questao(id_, categoria=None, texto_associado=None):
    return {"id": id_, "categoria": categoria, "texto_associado": texto_associado}


def test_ordenar_questoes_portugues_segue_precedencia_pedagogica():
    """A prova real começa por interpretação, não por gramática (achado do
    relatório de bug do simulado do PMDF)."""
    embaralhadas = [
        _questao(1, categoria="Sintaxe"),
        _questao(2, categoria="Interpretação de Textos"),
        _questao(3, categoria="Morfologia"),
        _questao(4, categoria="Ortografia"),
    ]
    ordenadas = taxonomia.ordenar_questoes(embaralhadas, "Língua Portuguesa")
    assert [q["id"] for q in ordenadas] == [2, 4, 3, 1]


def test_ordenar_questoes_aceita_portugues_sem_lingua():
    """Alguns editais chamam a matéria só de "Português" (ex.: Banco do Brasil)."""
    embaralhadas = [_questao(1, categoria="Sintaxe"), _questao(2, categoria="Ortografia")]
    ordenadas = taxonomia.ordenar_questoes(embaralhadas, "Português")
    assert [q["id"] for q in ordenadas] == [2, 1]


def test_ordenar_questoes_categoria_desconhecida_vai_pro_fim_mas_nao_quebra():
    """Sem categoria reconhecida, não inventa posição — só não atrapalha as
    que têm dado real (mesmo princípio do guardrail de `resolver`)."""
    embaralhadas = [
        _questao(1, categoria="Sintaxe"),
        _questao(2, categoria=None),
        _questao(3, categoria="Interpretação de Textos"),
    ]
    ordenadas = taxonomia.ordenar_questoes(embaralhadas, "Língua Portuguesa")
    assert [q["id"] for q in ordenadas] == [3, 1, 2]


def test_ordenar_questoes_materia_sem_matriz_mantem_ordem_original():
    """Só Português tem matriz por ora; outra matéria não arrisca palpite."""
    embaralhadas = [_questao(1, categoria="Z"), _questao(2, categoria="A")]
    assert taxonomia.ordenar_questoes(embaralhadas, "Direito Administrativo") == embaralhadas


def test_agrupar_por_texto_associado_junta_questoes_espalhadas():
    """Duas questões do mesmo texto-base, com uma questão solta no meio."""
    questoes = [
        _questao(1, texto_associado="Texto A"),
        _questao(2, texto_associado=None),
        _questao(3, texto_associado="Texto A"),
        _questao(4, texto_associado="Texto B"),
        _questao(5, texto_associado=None),
    ]
    agrupadas = taxonomia.agrupar_por_texto_associado(questoes)
    assert [q["id"] for q in agrupadas] == [1, 3, 2, 4, 5]


def test_agrupar_por_texto_associado_sem_nenhum_texto_mantem_ordem():
    questoes = [_questao(1), _questao(2), _questao(3)]
    assert taxonomia.agrupar_por_texto_associado(questoes) == questoes
