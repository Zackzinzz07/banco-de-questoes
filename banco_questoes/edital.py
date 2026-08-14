"""Matérias e assuntos do Edital nº 1/2026 SEDES/DF (cargo 202, itens 20.2.2/20.2.3)."""

_BASE_QC = ("https://www.qconcursos.com/questoes-de-concursos/questoes"
            "?exclude_nullified=true&exclude_outdated=true")

MATERIAS = {
    "Língua Portuguesa": {
        "assuntos": [
            "Compreensão e interpretação de textos",
            "Gêneros e tipos textuais",
            "Ortografia oficial",
            "Coesão e coerência",
            "Morfossintaxe",
            "Pontuação",
            "Concordância verbal e nominal",
            "Regência verbal e nominal",
            "Crase",
            "Substituição e reescrita de trechos",
        ],
        "titulos_pdf": ["LÍNGUA PORTUGUESA", "PORTUGUÊS"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=1",
    },
    "Conhecimentos do DF e Legislação": {
        "assuntos": [
            "DF e RIDE (LC nº 94/1998)",
            "Plano Diretor de Ordenamento Territorial (PDOT/PDPM)",
            "Lei Orgânica do DF (Título VI)",
            "LC nº 840/2011 (Títulos I, V, VI e VII)",
            "Lei Maria da Penha (Lei nº 11.340/2006)",
            "Lei Distrital nº 7.484/2024",
            "Noções de primeiros socorros",
        ],
        "titulos_pdf": ["CONHECIMENTOS SOBRE O DISTRITO FEDERAL", "REALIDADE DO DF",
                        "CONHECIMENTOS GERAIS DO DF", "LEGISLAÇÃO APLICADA"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=61",
    },
    "SUAS": {
        "assuntos": [
            "PNAS/2004",
            "SUAS: princípios e seguranças socioassistenciais",
            "NOB/SUAS 2012",
        ],
        "titulos_pdf": ["SUAS", "ASSISTÊNCIA SOCIAL", "POLÍTICA NACIONAL DE ASSISTÊNCIA SOCIAL"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=188",
    },
    "Programas e Benefícios do DF": {
        "assuntos": [
            "Cartão Prato Cheio (Lei nº 7.009/2021)",
            "Cartão Gás (Lei nº 6.938/2021)",
            "Plano DF Social (Lei nº 7.008/2021)",
            "Benefícios Eventuais (Lei nº 5.165/2013)",
            "SISAN e Restaurantes Comunitários (Decreto nº 33.329/2011)",
        ],
        "titulos_pdf": ["PROGRAMAS E BENEFÍCIOS", "PROGRAMAS SOCIAIS DO DF"],
        "url_qc": "",
    },
    "Direito Constitucional": {
        "assuntos": [
            "Princípios fundamentais",
            "Direitos e garantias fundamentais",
            "Organização do Estado",
            "Organização da Administração",
            "Servidores públicos",
        ],
        "titulos_pdf": ["DIREITO CONSTITUCIONAL", "NOÇÕES DE DIREITO CONSTITUCIONAL"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=3",
    },
    "Direito Administrativo": {
        "assuntos": [
            "Estado, governo e administração pública",
            "Ato administrativo",
            "Poderes administrativos",
            "LC nº 840/2011: provimento, vacância e processo disciplinar",
        ],
        "titulos_pdf": ["DIREITO ADMINISTRATIVO", "NOÇÕES DE DIREITO ADMINISTRATIVO"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=2",
    },
    "Atendimento, Rotinas Administrativas e Arquivologia": {
        "assuntos": [
            "Qualidade no atendimento ao público",
            "Redação oficial",
            "Rotinas administrativas e protocolo",
            "Métodos de arquivamento",
            "Digitalização e gestão de documentos",
        ],
        "titulos_pdf": ["ARQUIVOLOGIA", "ROTINAS ADMINISTRATIVAS", "ATENDIMENTO AO PÚBLICO",
                        "NOÇÕES DE ARQUIVOLOGIA"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=20&discipline_ids%5B%5D=187&discipline_ids%5B%5D=174",
    },
    "Recursos Materiais, Patrimônio e Compras": {
        "assuntos": [
            "Gestão de estoques",
            "Armazenagem e movimentação de materiais",
            "Gestão patrimonial: tombamento, inventário e baixa",
            "Lei nº 14.133/2021 (licitações e contratos)",
        ],
        "titulos_pdf": ["RECURSOS MATERIAIS", "ADMINISTRAÇÃO DE MATERIAL", "LICITAÇ"],
        "url_qc": _BASE_QC + "&discipline_ids%5B%5D=213",
    },
}


def nomes_materias():
    return list(MATERIAS)


def materia_por_titulo(titulo):
    """Casa um cabeçalho de seção de prova com a matéria canônica (ou None)."""
    t = " ".join(titulo.split()).upper()
    for nome, dados in MATERIAS.items():
        for padrao in dados["titulos_pdf"]:
            if padrao in t:
                return nome
    return None


# Pesos para o Simulado Geral (distribuição real do edital SEDES 2026).
# Bloco Genérico (20 questões): Peso 1
# Bloco Específico (40 questões): Peso 2
PESOS = {
    "Língua Portuguesa": 10,  # 10 do bloco genérico
    "Conhecimentos do DF e Legislação": 10,  # 10 do bloco genérico (inclui Maria da Penha, LC 840/2011, etc)
    "SUAS": 10,  # 10 do bloco específico
    "Programas e Benefícios do DF": 10,  # 10 do bloco específico
    "Direito Administrativo": 5,  # 5 do bloco específico
    "Direito Constitucional": 5,  # 5 do bloco específico
    "Atendimento, Rotinas Administrativas e Arquivologia": 5,  # 5 do bloco específico
    "Recursos Materiais, Patrimônio e Compras": 5,  # 5 do bloco específico
}


def distribuir_por_peso(quantidade):
    """Divide a quantidade entre as matérias proporcionalmente aos PESOS."""
    total_pesos = sum(PESOS.values())
    exatas = {m: quantidade * p / total_pesos for m, p in PESOS.items()}
    dist = {m: int(v) for m, v in exatas.items()}
    sobra = quantidade - sum(dist.values())
    ordem = sorted(exatas, key=lambda m: exatas[m] - dist[m], reverse=True)
    for m in ordem[:sobra]:
        dist[m] += 1
    return dist
