import edital


def test_oito_materias_canonicas():
    assert edital.nomes_materias() == [
        "Língua Portuguesa",
        "Conhecimentos do DF e Legislação",
        "SUAS",
        "Programas e Benefícios do DF",
        "Direito Constitucional",
        "Direito Administrativo",
        "Atendimento, Rotinas Administrativas e Arquivologia",
        "Recursos Materiais, Patrimônio e Compras",
    ]


def test_toda_materia_tem_assuntos_e_titulos():
    for nome, dados in edital.MATERIAS.items():
        assert dados["assuntos"], nome
        assert dados["titulos_pdf"], nome
        assert "url_qc" in dados, nome


def test_materia_por_titulo():
    assert edital.materia_por_titulo("LÍNGUA PORTUGUESA") == "Língua Portuguesa"
    assert edital.materia_por_titulo("  Língua  Portuguesa ") == "Língua Portuguesa"
    assert edital.materia_por_titulo("NOÇÕES DE DIREITO ADMINISTRATIVO") == "Direito Administrativo"
    assert edital.materia_por_titulo("MATEMÁTICA") is None
