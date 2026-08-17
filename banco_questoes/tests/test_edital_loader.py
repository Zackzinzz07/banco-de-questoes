"""Tests for dynamic edital loader with YAML support and fallback."""

import pytest
from banco_questoes.edital_loader import (
    listar_concursos,
    carregar_edital,
    listar_cargos,
    obter_materias,
    obter_pesos,
    distribuir_por_peso,
    obter_assuntos,
)


class TestListarConcursos:
    """Test listing available concursos."""

    def test_lista_sete_concursos(self):
        """Should list exactly 7 concursos."""
        concursos = listar_concursos()
        assert len(concursos) == 7

    def test_contem_todos_concursos(self):
        """Should contain all expected concursos."""
        concursos = listar_concursos()
        esperados = {
            "sedes_df",
            "prf",
            "bacen",
            "receita_federal",
            "inss",
            "correios",
            "banco_brasil",
        }
        assert set(concursos) == esperados

    def test_tipos_strings(self):
        """All concursos should be strings."""
        concursos = listar_concursos()
        assert all(isinstance(c, str) for c in concursos)


class TestCarregarEdital:
    """Test loading edital configurations."""

    def test_carregar_sedes_df(self):
        """Should load SEDES/DF edital from YAML."""
        edital = carregar_edital("sedes_df")
        assert edital is not None
        assert edital["banca"] == "Instituto Quadrix"
        assert edital["total_questoes"] == 60
        assert edital["ano"] == 2026

    def test_carregar_prf(self):
        """Should load PRF edital from YAML."""
        edital = carregar_edital("prf")
        assert edital["banca"] == "Cebraspe"
        assert edital["total_questoes"] == 120
        assert edital["formato"] == "Certo_Errado"

    def test_carregar_bacen(self):
        """Should load BACEN edital from YAML."""
        edital = carregar_edital("bacen")
        assert edital["banca"] == "Cebraspe"
        assert edital["total_questoes"] == 120
        assert "Analista Técnico - Tecnologia da Informação" in edital["cargos"]
        assert "Analista Técnico - Economia" in edital["cargos"]

    def test_carregar_receita_federal(self):
        """Should load Receita Federal edital from YAML."""
        edital = carregar_edital("receita_federal")
        assert edital["banca"] == "FGV"
        assert edital["total_questoes"] == 140

    def test_carregar_inss(self):
        """Should load INSS edital from YAML."""
        edital = carregar_edital("inss")
        assert edital["banca"] == "Cebraspe"
        assert edital["total_questoes"] == 120

    def test_carregar_correios(self):
        """Should load Correios edital from YAML."""
        edital = carregar_edital("correios")
        assert edital["banca"] == "IBFC"
        assert edital["total_questoes"] == 50

    def test_carregar_banco_brasil(self):
        """Should load Banco Brasil edital from YAML."""
        edital = carregar_edital("banco_brasil")
        assert edital["banca"] == "Cesgranrio"
        assert edital["total_questoes"] == 70

    def test_edital_invalido_retorna_none(self):
        """Should return None for invalid concurso."""
        edital = carregar_edital("concurso_inexistente")
        assert edital is None

    def test_edital_tem_estrutura_basica(self):
        """Loaded edital should have basic structure."""
        edital = carregar_edital("prf")
        assert "nome" in edital
        assert "banca" in edital
        assert "ano" in edital
        assert "orgao" in edital
        assert "formato" in edital
        assert "total_questoes" in edital
        assert "tempo_minutos" in edital
        assert "cargos" in edital


class TestListarCargos:
    """Test listing cargos for a concurso."""

    def test_cargos_prf(self):
        """PRF should have one cargo."""
        cargos = listar_cargos("prf")
        assert len(cargos) == 1
        assert "Policial Rodoviário Federal" in cargos

    def test_cargos_bacen(self):
        """BACEN should have two cargos."""
        cargos = listar_cargos("bacen")
        assert len(cargos) == 2
        assert "Analista Técnico - Tecnologia da Informação" in cargos
        assert "Analista Técnico - Economia" in cargos

    def test_cargos_sedes_df(self):
        """SEDES/DF should have one cargo."""
        cargos = listar_cargos("sedes_df")
        assert len(cargos) == 1
        assert "Técnico de Atendimento Direto ao Cidadão" in cargos

    def test_cargos_receita_federal(self):
        """Receita Federal should have two cargos."""
        cargos = listar_cargos("receita_federal")
        assert len(cargos) == 2
        assert "Auditor-Fiscal da Receita Federal" in cargos
        assert "Analista-Tributário da Receita Federal" in cargos

    def test_cargos_concurso_invalido(self):
        """Should return empty list for invalid concurso."""
        cargos = listar_cargos("concurso_inexistente")
        assert cargos == []

    def test_tipos_strings(self):
        """All cargos should be strings."""
        cargos = listar_cargos("prf")
        assert all(isinstance(c, str) for c in cargos)


class TestObterMaterias:
    """Test retrieving subjects for a concurso/cargo."""

    def test_materias_prf(self):
        """PRF Policial should have Legislação de Trânsito."""
        materias = obter_materias("prf", "Policial Rodoviário Federal")
        assert materias is not None
        assert "Legislação de Trânsito" in materias
        assert materias["Legislação de Trânsito"]["pesos"] == 30

    def test_materias_bacen_ti(self):
        """BACEN TI area should have Ciência de Dados."""
        materias = obter_materias("bacen", "Analista Técnico - Tecnologia da Informação")
        assert materias is not None
        assert "Ciência de Dados" in materias
        assert materias["Ciência de Dados"]["pesos"] == 20

    def test_materias_bacen_economia(self):
        """BACEN Economia area should have Macroeconomia."""
        materias = obter_materias("bacen", "Analista Técnico - Economia")
        assert materias is not None
        assert "Macroeconomia" in materias
        assert materias["Macroeconomia"]["pesos"] == 15

    def test_materias_inss(self):
        """INSS should have Seguridade Social = 60."""
        materias = obter_materias("inss", "Técnico de Seguro Social")
        assert materias is not None
        assert "Seguridade Social" in materias
        assert materias["Seguridade Social"]["pesos"] == 60

    def test_materias_banco_brasil_agente_tech(self):
        """BB Agente Tech should have TI = 35."""
        materias = obter_materias("banco_brasil", "Agente de Tecnologia")
        assert materias is not None
        assert "Tecnologia da Informação" in materias
        assert materias["Tecnologia da Informação"]["pesos"] == 35

    def test_materias_cargo_invalido(self):
        """Should return None for invalid cargo."""
        materias = obter_materias("prf", "Cargo Inexistente")
        assert materias is None

    def test_materias_concurso_invalido(self):
        """Should return None for invalid concurso."""
        materias = obter_materias("concurso_inexistente", "Cargo")
        assert materias is None

    def test_materias_estrutura(self):
        """Materias should have pesos and assuntos keys."""
        materias = obter_materias("prf", "Policial Rodoviário Federal")
        for materia_nome, dados in materias.items():
            assert "pesos" in dados
            assert "assuntos" in dados
            assert isinstance(dados["pesos"], int)
            assert isinstance(dados["assuntos"], list)


class TestObterPesos:
    """Test getting weight distribution for a concurso/cargo."""

    def test_pesos_prf(self):
        """PRF pesos should sum to 120."""
        pesos = obter_pesos("prf", "Policial Rodoviário Federal")
        assert sum(pesos.values()) == 120
        assert pesos["Legislação de Trânsito"] == 30

    def test_pesos_bacen_ti(self):
        """BACEN TI pesos should sum correctly."""
        pesos = obter_pesos("bacen", "Analista Técnico - Tecnologia da Informação")
        assert sum(pesos.values()) == 120

    def test_pesos_inss(self):
        """INSS pesos should sum to 120."""
        pesos = obter_pesos("inss", "Técnico de Seguro Social")
        assert sum(pesos.values()) == 120
        assert pesos["Seguridade Social"] == 60

    def test_pesos_cargo_invalido(self):
        """Should return empty dict for invalid cargo."""
        pesos = obter_pesos("prf", "Cargo Inexistente")
        assert pesos == {}

    def test_pesos_todos_positivos(self):
        """All pesos should be positive integers."""
        pesos = obter_pesos("prf", "Policial Rodoviário Federal")
        assert all(p > 0 for p in pesos.values())
        assert all(isinstance(p, int) for p in pesos.values())


class TestDistribuirPorPeso:
    """Test weight-based question distribution."""

    def test_distribuir_quantidade_exata(self):
        """Distribution should equal requested quantity."""
        pesos = {"Português": 10, "Direito": 5}
        dist = distribuir_por_peso(60, pesos)
        assert sum(dist.values()) == 60

    def test_distribuir_proporcional(self):
        """Distribution should be proportional to weights."""
        pesos = {"Português": 10, "Direito": 5}
        dist = distribuir_por_peso(60, pesos)
        assert dist["Português"] == 40
        assert dist["Direito"] == 20

    def test_distribuir_pequena_quantidade(self):
        """Should handle small quantities."""
        pesos = {"A": 1, "B": 1, "C": 1}
        dist = distribuir_por_peso(3, pesos)
        assert sum(dist.values()) == 3
        assert all(v == 1 for v in dist.values())

    def test_distribuir_quantidade_zero(self):
        """Should handle zero quantity."""
        pesos = {"A": 1, "B": 1}
        dist = distribuir_por_peso(0, pesos)
        assert sum(dist.values()) == 0

    def test_distribuir_diferentes_quantidades(self):
        """Should work with various quantities."""
        pesos = {"A": 10, "B": 5, "C": 5}
        for quantidade in (8, 20, 33, 60, 70, 100):
            dist = distribuir_por_peso(quantidade, pesos)
            assert sum(dist.values()) == quantidade
            assert set(dist.keys()) == set(pesos.keys())

    def test_distribuir_pesos_desiguais(self):
        """Subject with higher weight should get more questions."""
        pesos = {"Português": 20, "Matemática": 10}
        dist = distribuir_por_peso(60, pesos)
        assert dist["Português"] >= dist["Matemática"]


class TestObterAssuntos:
    """Test getting assuntos (topics) for a subject."""

    def test_obter_assuntos_prf(self):
        """Should return assuntos for PRF subjects (empty for now, placeholder)."""
        assuntos = obter_assuntos("prf", "Policial Rodoviário Federal", "Português")
        assert isinstance(assuntos, list)
        # Currently returns empty list as placeholder (YAML doesn't have topic data yet)

    def test_obter_assuntos_invalido_materia(self):
        """Should return empty list for invalid subject."""
        assuntos = obter_assuntos("prf", "Policial Rodoviário Federal", "Matéria Inexistente")
        assert assuntos == []

    def test_obter_assuntos_invalido_cargo(self):
        """Should return empty list for invalid cargo."""
        assuntos = obter_assuntos("prf", "Cargo Inexistente", "Português")
        assert assuntos == []

    def test_obter_assuntos_invalido_concurso(self):
        """Should return empty list for invalid concurso."""
        assuntos = obter_assuntos("concurso_inexistente", "Cargo", "Matéria")
        assert assuntos == []


class TestFallbackSedesDF:
    """Test fallback behavior for SEDES/DF."""

    def test_fallback_com_yaml_existente(self):
        """SEDES/DF should work with YAML file."""
        edital = carregar_edital("sedes_df")
        assert edital is not None
        assert edital["banca"] == "Instituto Quadrix"

    def test_materias_com_yaml(self):
        """Should get materias from YAML."""
        cargos = listar_cargos("sedes_df")
        assert len(cargos) > 0
        materias = obter_materias("sedes_df", cargos[0])
        assert materias is not None
        assert len(materias) == 8  # SEDES tem 8 matérias


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_workflow_completo_prf(self):
        """Complete workflow for PRF."""
        # List concursos
        concursos = listar_concursos()
        assert "prf" in concursos

        # Load edital
        edital = carregar_edital("prf")
        assert edital is not None

        # List cargos
        cargos = listar_cargos("prf")
        assert len(cargos) > 0

        # Get materias
        cargo = cargos[0]
        materias = obter_materias("prf", cargo)
        assert materias is not None

        # Get pesos
        pesos = obter_pesos("prf", cargo)
        assert sum(pesos.values()) == edital["total_questoes"]

        # Distribute questions
        dist = distribuir_por_peso(edital["total_questoes"], pesos)
        assert sum(dist.values()) == edital["total_questoes"]

    def test_workflow_bacen_ambas_areas(self):
        """Test both BACEN areas."""
        cargos = listar_cargos("bacen")
        assert len(cargos) == 2

        for cargo in cargos:
            materias = obter_materias("bacen", cargo)
            assert materias is not None
            pesos = obter_pesos("bacen", cargo)
            assert sum(pesos.values()) == 120
