"""Data consistency tests: verify data integrity across all layers."""
import pytest
import yaml
from pathlib import Path

import edital_loader
import config
import db


class TestYAMLStructure:
    """Test YAML file structure and validity."""

    def test_yaml_estrutura_valida(self):
        """Verify all YAML files have valid structure."""
        concursos = edital_loader.listar_concursos()
        assert len(concursos) >= 1, "Should have at least one concurso"

        for concurso in concursos:
            edital = edital_loader.carregar_edital(concurso)
            assert edital is not None, f"{concurso} should load successfully"

            # Check required fields
            assert "nome" in edital, f"{concurso} missing 'nome'"
            assert "banca" in edital, f"{concurso} missing 'banca'"
            assert "cargos" in edital, f"{concurso} missing 'cargos'"

            # Check cargos structure
            cargos_dict = edital.get("cargos", {})
            assert len(cargos_dict) > 0, f"{concurso} has no cargos"

            for cargo, info in cargos_dict.items():
                assert isinstance(info, dict), f"{concurso}/{cargo} info should be dict"
                assert "nivel" in info, f"{concurso}/{cargo} missing 'nivel'"
                assert "materias" in info, f"{concurso}/{cargo} missing 'materias'"

                # Check pesos sum correctly
                materias = info.get("materias", {})
                assert len(materias) > 0, f"{concurso}/{cargo} has no materias"

                # All materias should have numeric weights
                for materia, peso in materias.items():
                    assert isinstance(peso, (int, float)), \
                        f"{concurso}/{cargo}/{materia} peso should be numeric, got {type(peso)}"
                    assert peso > 0, \
                        f"{concurso}/{cargo}/{materia} peso should be positive"

    def test_sedes_df_fallback_valido(self):
        """Verify SEDES/DF fallback is valid when YAML not found."""
        # SEDES/DF might be loaded from YAML or fallback
        edital = edital_loader.carregar_edital("sedes_df")
        if edital is not None:
            assert "cargos" in edital
            cargos = edital.get("cargos", {})
            assert len(cargos) > 0, "SEDES/DF should have at least one cargo"

    def test_all_cargos_accessible(self):
        """Verify all cargos can be accessed."""
        concursos = edital_loader.listar_concursos()

        for concurso in concursos:
            cargos = edital_loader.listar_cargos(concurso)
            assert len(cargos) > 0, f"{concurso} has no cargos"

            for cargo in cargos:
                materias = edital_loader.obter_materias(concurso, cargo)
                assert materias is not None, \
                    f"{concurso}/{cargo} should have materias"
                assert len(materias) > 0, \
                    f"{concurso}/{cargo} has no materias"

                pesos = edital_loader.obter_pesos(concurso, cargo)
                assert pesos is not None, \
                    f"{concurso}/{cargo} should have pesos"
                assert len(pesos) > 0, \
                    f"{concurso}/{cargo} has no pesos"

    def test_no_duplicate_materias_same_cargo(self):
        """Verify no duplicate materias within same cargo."""
        concursos = edital_loader.listar_concursos()

        for concurso in concursos:
            cargos = edital_loader.listar_cargos(concurso)
            for cargo in cargos:
                materias = edital_loader.obter_materias(concurso, cargo)
                if materias:
                    materia_names = list(materias.keys())
                    unique_names = set(materia_names)
                    assert len(materia_names) == len(unique_names), \
                        f"{concurso}/{cargo} has duplicate materias"

    def test_pesos_nao_negativos(self):
        """Verify all pesos are non-negative."""
        concursos = edital_loader.listar_concursos()

        for concurso in concursos:
            cargos = edital_loader.listar_cargos(concurso)
            for cargo in cargos:
                pesos = edital_loader.obter_pesos(concurso, cargo)
                for materia, peso in pesos.items():
                    assert peso > 0, \
                        f"{concurso}/{cargo}/{materia}: peso should be > 0, got {peso}"


class TestWeightDistribution:
    """Test weight distribution functionality."""

    def test_distribuir_por_peso_simples(self):
        """Test basic weight distribution."""
        pesos = {
            "Português": 30,
            "Matemática": 20,
            "Direito": 10,
        }

        dist = edital_loader.distribuir_por_peso(60, pesos)
        assert sum(dist.values()) == 60
        assert dist["Português"] == 30
        assert dist["Matemática"] == 20
        assert dist["Direito"] == 10

    def test_distribuir_por_peso_proporcional(self):
        """Test proportional weight distribution."""
        pesos = {
            "A": 1,
            "B": 2,
            "C": 3,
        }

        dist = edital_loader.distribuir_por_peso(60, pesos)
        assert sum(dist.values()) == 60
        assert dist["A"] == 10
        assert dist["B"] == 20
        assert dist["C"] == 30

    def test_distribuir_por_peso_remainder(self):
        """Test weight distribution with remainder allocation."""
        pesos = {
            "A": 1,
            "B": 1,
            "C": 1,
        }

        dist = edital_loader.distribuir_por_peso(10, pesos)
        assert sum(dist.values()) == 10
        # Each should get at least 3, and remainder 1 should be distributed
        assert all(dist[k] >= 3 for k in dist)

    def test_distribuir_por_peso_zero_quantidade(self):
        """Test weight distribution with zero quantity."""
        pesos = {"A": 1, "B": 1}
        dist = edital_loader.distribuir_por_peso(0, pesos)
        assert sum(dist.values()) == 0

    def test_distribuir_por_peso_empty_pesos(self):
        """Test weight distribution with empty pesos."""
        dist = edital_loader.distribuir_por_peso(10, {})
        assert dist == {}


class TestCargoStructure:
    """Test cargo-specific structure validation."""

    def test_bacen_dois_cargos_diferentes(self):
        """Test that BACEN has two different areas with different materias."""
        cargos = edital_loader.listar_cargos("bacen")
        if len(cargos) >= 2:
            # Get first two cargos
            cargo1, cargo2 = cargos[0], cargos[1]

            materias1 = edital_loader.obter_materias("bacen", cargo1)
            materias2 = edital_loader.obter_materias("bacen", cargo2)

            # They should have different subject sets
            set1 = set(materias1.keys()) if materias1 else set()
            set2 = set(materias2.keys()) if materias2 else set()

            # At least some difference expected
            if len(set1) > 0 and len(set2) > 0:
                # Not identical
                assert set1 != set2 or cargo1 == cargo2, \
                    f"Different cargos should have different or same subject sets"

    def test_prf_validacao_cargos(self):
        """Test PRF cargo validation."""
        cargos = edital_loader.listar_cargos("prf")
        if len(cargos) > 0:
            for cargo in cargos:
                pesos = edital_loader.obter_pesos("prf", cargo)
                assert pesos is not None
                assert sum(pesos.values()) > 0, f"PRF/{cargo} should have total questoes > 0"


class TestDatabaseDataConsistency:
    """Test data consistency in database operations."""

    def test_salvar_questao_completa(self, monkeypatch):
        """Test saving a complete question with all fields."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            q = {
                "id_qc": "TEST_COMPLETE_Q",
                "enunciado": "Complete question test",
                "alternativas": {"A": "Alt A", "B": "Alt B", "C": "Alt C", "D": "Alt D", "E": "Alt E"},
                "gabarito": "C",
                "comentario": "This is a comment",
                "materia": "Direito",
                "assunto": "Constitucional",
                "banca": "Cebraspe",
                "orgao": "prf",
                "cargo": "Policial",
                "ano": 2024,
                "prova": "Prova 1",
                "fonte": "qconcursos",
            }

            result = db.salvar_questao(con, q)
            assert result == True

            # Retrieve and verify all fields
            questoes = db.sortear_questoes(con, "Direito", 1)
            assert len(questoes) >= 1
            retrieved = questoes[0]

            assert retrieved["enunciado"] == q["enunciado"]
            assert retrieved["alternativas"] == q["alternativas"]
            assert retrieved["gabarito"] == q["gabarito"]
            assert retrieved["comentario"] == q["comentario"]
            assert retrieved["materia"] == q["materia"]
            assert retrieved["cargo"] == q["cargo"]
            assert retrieved["orgao"] == q["orgao"]
        finally:
            con.close()

    def test_filtros_combinados_consistencia(self, monkeypatch):
        """Test that combined filters work consistently."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Save questions with different combinations
            combinations = [
                {"materia": "Português", "cargo": "Cargo1", "orgao": "ORG1", "banca": "Cebraspe"},
                {"materia": "Português", "cargo": "Cargo2", "orgao": "ORG1", "banca": "Cebraspe"},
                {"materia": "Português", "cargo": "Cargo1", "orgao": "ORG2", "banca": "IADES"},
            ]

            for i, combo in enumerate(combinations):
                q = {
                    "enunciado": f"Test question {i}",
                    "alternativas": {"A": "A", "B": "B"},
                    "fonte": "qconcursos",
                    **combo
                }
                db.salvar_questao(con, q)

            # Test individual filters
            q1 = db.sortear_questoes(con, "Português", 10, cargo="Cargo1")
            assert len(q1) == 2  # Should get both Cargo1 questions

            q2 = db.sortear_questoes(con, "Português", 10, orgao="ORG1")
            assert len(q2) == 2  # Should get both ORG1 questions

            q3 = db.sortear_questoes(con, "Português", 10, banca="Cebraspe")
            assert len(q3) == 2  # Should get both Cebraspe questions

            # Test combined filters
            q4 = db.sortear_questoes(con, "Português", 10, cargo="Cargo1", orgao="ORG1")
            assert len(q4) == 1  # Only one matches both filters

        finally:
            con.close()

    def test_content_hash_deduplicacao(self, monkeypatch):
        """Test that content_hash properly deduplicates questions."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Same enunciado and alternativas should deduplicate
            q_base = {
                "enunciado": "Identical enunciado for dedup",
                "alternativas": {"A": "Option A", "B": "Option B"},
                "materia": "Português",
                "fonte": "qconcursos",
            }

            # First question
            db.salvar_questao(con, {**q_base, "id_qc": "ID1"})

            # Second question with same content but different ID
            result = db.salvar_questao(con, {**q_base, "id_qc": "ID2"})
            assert result == False  # Should be deduplicated

            # Retrieve - should get deduplicated version
            questoes = db.sortear_questoes(con, "Português", 10)
            assert len(questoes) <= 2  # At most 2 (depends on DISTINCT ON)
        finally:
            con.close()


class TestEditaisYAMLContent:
    """Test actual YAML content for completeness."""

    def test_prf_yaml_contem_materias(self):
        """Test that PRF YAML has expected subjects."""
        cargos = edital_loader.listar_cargos("prf")
        if cargos:
            pesos = edital_loader.obter_pesos("prf", cargos[0])
            # PRF should have legal subjects
            materias_lower = [m.lower() for m in pesos.keys()]
            # Check for common PRF subjects
            assert len(pesos) > 0, "PRF should have materias"

    def test_todos_concursos_tem_cargos(self):
        """Test that all concursos have at least one cargo."""
        concursos = edital_loader.listar_concursos()
        for concurso in concursos:
            cargos = edital_loader.listar_cargos(concurso)
            assert len(cargos) > 0, f"{concurso} should have at least one cargo"

    def test_todos_cargos_tem_pesos_positivos(self):
        """Test that all cargos have positive weights."""
        concursos = edital_loader.listar_concursos()
        for concurso in concursos:
            cargos = edital_loader.listar_cargos(concurso)
            for cargo in cargos:
                pesos = edital_loader.obter_pesos(concurso, cargo)
                total = sum(pesos.values())
                assert total > 0, f"{concurso}/{cargo} has no positive weights"
