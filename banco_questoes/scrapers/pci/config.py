"""Categorias e mapeamento de temas do PCI Concursos (config estática).

Extraído do protótipo `config_pci.py` (removido na migração para o pacote
modular `scrapers/`). Sem I/O — apenas dados e pequenos helpers de leitura.
"""

# Categorias do PCI Concursos (42 totais).
# slug -> (nome_display, quantidade_total_aproximada)
PCI_CATEGORIAS = {
    "administracao-publica": ("Administração Pública", 3597),
    "artes": ("Artes", 236),
    "atualidades": ("Atualidades", 1639),
    "biblioteconomia": ("Biblioteconomia", 374),
    "biologia": ("Biologia", 119),
    "contabilidade": ("Contabilidade", 1635),
    "direito-administrativo": ("Direito Administrativo", 7479),
    "direito-ambiental": ("Direito Ambiental", 149),
    "direito-constitucional": ("Direito Constitucional", 2124),
    "direito-financeiro": ("Direito Financeiro", 414),
    "direito-penal": ("Direito Penal", 248),
    "direito-processual-civil": ("Direito Processual Civil", 33),
    "direito-trabalhista": ("Direito Trabalhista", 44),
    "direito-tributario": ("Direito Tributário", 411),
    "economia": ("Economia", 32),
    "educacao": ("Educação", 93),
    "enfermagem": ("Enfermagem", 931),
    "engenharia-civil": ("Engenharia Civil", 652),
    "filosofia": ("Filosofia", 96),
    "fisica": ("Física", 138),
    "historia": ("História", 3173),
    "informatica": ("Informática", 11809),
    "ingles": ("Inglês", 427),
    "legislacao-especifica": ("Legislação Específica", 8349),
    "matematica": ("Matemática", 8841),
    "meio-ambiente": ("Meio Ambiente", 415),
    "musica": ("Música", 242),
    "outra": ("Outra", 1335),
    "pedagogia": ("Pedagogia", 12692),
    "portugues": ("Português", 9797),
    "psicologia": ("Psicologia", 838),
    "quimica": ("Química", 247),
    "raciocinio-logico-matematico": ("Raciocínio Lógico Matemático", 570),
    "saude": ("Saúde", 28191),
    "saude-publica": ("Saúde Pública", 13279),
    "seguranca-do-trabalho": ("Segurança do Trabalho", 1969),
    "seguranca-publica": ("Segurança Pública", 40),
    "servico-social": ("Serviço Social", 934),
    "sociologia": ("Sociologia", 92),
    "testes-anteriores": ("Testes Anteriores", 127945),
    "transito": ("Trânsito", 569),
}

# Mapeamento de categorias PCI para matérias genéricas.
# Estratégia: capturar TUDO do PCI com mapeamento simples categoria -> matéria
# Depois a gente reorganiza conforme necessário para cada concurso.
MAPEAMENTO_TEMAS = {
    # Administração Pública (22 temas mapeados)
    "administracao-publica/atendimento-ao-cidadao": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/atendimento-ao-publico": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/comportamento-organizacional": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/comunicacao-organizacional": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/cultura-organizacional": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/estrutura-organizacional": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/etica-no-servico-publico": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/funcoes-administrativas": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-da-qualidade": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-de-processos": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-documental": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-de-estoques": "Recursos Materiais, Patrimônio e Compras",
    "administracao-publica/gestao-estrategica": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-de-materiais": "Recursos Materiais, Patrimônio e Compras",
    "administracao-publica/gestao-de-pessoas": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-de-projetos": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/gestao-publica": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/lideranca": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/planejamento-estrategico": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/politicas-publicas": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/relacionamento-interpessoal": "Atendimento, Rotinas Administrativas e Arquivologia",
    "administracao-publica/teorias-da-administracao": "Atendimento, Rotinas Administrativas e Arquivologia",

    # Direito
    "direito-administrativo/*": "Direito Administrativo",
    "direito-constitucional/*": "Direito Constitucional",
    "direito-ambiental/*": "Direito Ambiental",
    "direito-financeiro/*": "Direito Financeiro",
    "direito-penal/*": "Direito Penal",
    "direito-processual-civil/*": "Direito Processual Civil",
    "direito-trabalhista/*": "Direito Trabalhista",
    "direito-tributario/*": "Direito Tributário",

    # Linguagem
    "portugues/*": "Língua Portuguesa",
    "ingles/*": "Inglês",

    # Humanidades
    "historia/*": "História",
    "geografia/*": "Geografia",
    "filosofia/*": "Filosofia",
    "sociologia/*": "Sociologia",
    "artes/*": "Artes",
    "musica/*": "Música",

    # Ciências Exatas
    "matematica/*": "Matemática",
    "fisica/*": "Física",
    "quimica/*": "Química",
    "raciocinio-logico-matematico/*": "Raciocínio Lógico Matemático",

    # Ciências da Natureza
    "biologia/*": "Biologia",
    "meio-ambiente/*": "Meio Ambiente",

    # Educação, Serviços Sociais, Saúde
    "educacao/*": "Educação",
    "pedagogia/*": "Pedagogia",
    "servico-social/*": "Serviço Social",
    "psicologia/*": "Psicologia",
    "enfermagem/*": "Enfermagem",
    "saude/*": "Saúde",
    "saude-publica/*": "Saúde Pública",
    "seguranca-do-trabalho/*": "Segurança do Trabalho",

    # Profissional/Técnico
    "informatica/*": "Informática",
    "biblioteconomia/*": "Biblioteconomia",
    "contabilidade/*": "Contabilidade",
    "engenharia-civil/*": "Engenharia Civil",

    # Legislação, Economia, Atualidades
    "legislacao-especifica/*": "Legislação Específica",
    "economia/*": "Economia",
    "atualidades/*": "Atualidades",
    "transito/*": "Legislação de Trânsito",
    "seguranca-publica/*": "Segurança Pública",

    # Genérico
    "outra/*": "Outros Conhecimentos",
}


def get_categoria_info(categoria_slug):
    """Retorna (nome, total_questoes) da categoria, ou (None, 0) se desconhecida."""
    return PCI_CATEGORIAS.get(categoria_slug, (None, 0))


def get_materia_do_tema(categoria, tema):
    """Retorna a matéria do edital para um tema específico.

    Tenta:
    1. Mapeamento exato: categoria/tema
    2. Fallback com wildcard: categoria/*
    3. Fallback só categoria
    """
    chave_exata = f"{categoria}/{tema}"
    if chave_exata in MAPEAMENTO_TEMAS:
        return MAPEAMENTO_TEMAS[chave_exata]

    chave_wildcard = f"{categoria}/*"
    if chave_wildcard in MAPEAMENTO_TEMAS:
        return MAPEAMENTO_TEMAS[chave_wildcard]

    # Se nada encontrou, retorna None (tema será pulado)
    return None


def listar_categorias():
    """Retorna a lista de slugs de todas as categorias conhecidas."""
    return list(PCI_CATEGORIAS.keys())
