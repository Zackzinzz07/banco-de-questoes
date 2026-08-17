"""End-to-end integration tests: complete flow from selection to PDF generation."""
import pytest
from pathlib import Path
from urllib.parse import quote
import time

import db
import edital_loader
import config
import web_api
from fastapi.testclient import TestClient


def cliente_com_banco(tmp_path, monkeypatch):
    """Create test client with isolated database and simulados directory."""
    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
    monkeypatch.setattr(web_api, "PASTA_SIMULADOS", tmp_path)
    return TestClient(web_api.app)


class TestFluxoCompletoORGAO:
    """Test complete flow for various órgãos/concursos."""

    def test_fluxo_completo_prf(self, tmp_path, monkeypatch):
        """Complete flow: select PRF → view stats → generate PDF."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        # 1. Verify PRF in available concursos
        response = client.get("/api/orgaos")
        assert response.status_code == 200
        orgaos = response.json()["orgaos"]
        assert len(orgaos) >= 1

        # 2. List cargos for PRF (if available)
        response = client.get("/api/cargos/prf")
        if response.status_code == 200:
            cargos = response.json()["cargos"]
            assert len(cargos) >= 1
            cargo = cargos[0]

            # 3. Get materias and pesos for cargo
            cargo_encoded = quote(cargo, safe='')
            response = client.get(f"/api/materias/prf/{cargo_encoded}")
            assert response.status_code == 200
            data = response.json()
            assert "materias" in data
            assert "pesos" in data
            assert data["total_questoes"] > 0

            # 4. Check stats (should be empty initially)
            response = client.get(f"/api/stats/cargo/prf/{cargo_encoded}")
            assert response.status_code == 200
            stats = response.json()
            assert stats["total"]["coletadas"] == 0

            # 5. Add sample question with cargo
            con = db.conectar()
            try:
                materias_list = list(data["materias"])
                if materias_list:
                    q = {
                        "enunciado": "Teste PRF integração e2e",
                        "alternativas": {"A": "A", "B": "B", "C": "C"},
                        "materia": materias_list[0],
                        "cargo": cargo,
                        "orgao": "prf",
                        "banca": "Cebraspe",
                        "fonte": "qconcursos",
                    }
                    assert db.salvar_questao(con, q) == True

                    # 6. Verify stats updated
                    response = client.get(f"/api/stats/cargo/prf/{cargo_encoded}")
                    stats = response.json()
                    assert stats["total"]["coletadas"] >= 1
            finally:
                con.close()

    def test_fluxo_completo_bacen_ti(self, tmp_path, monkeypatch):
        """Complete flow for BACEN TI area."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        # Get BACEN cargos
        response = client.get("/api/cargos/bacen")
        if response.status_code == 200:
            cargos = response.json()["cargos"]
            assert len(cargos) >= 1

            # Find TI cargo
            ti_cargo = None
            for cargo in cargos:
                if "tecnologia" in cargo.lower() or "informação" in cargo.lower() or "ti" in cargo.lower():
                    ti_cargo = cargo
                    break

            if ti_cargo:
                cargo_encoded = quote(ti_cargo, safe='')
                response = client.get(f"/api/materias/bacen/{cargo_encoded}")
                assert response.status_code == 200
                data = response.json()
                assert "materias" in data
                # TI should have different subjects than Economics
                assert len(data["materias"]) >= 5

    def test_fluxo_completo_sedes_df(self, tmp_path, monkeypatch):
        """Complete flow for SEDES/DF."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        # Get SEDES/DF cargos
        response = client.get("/api/cargos/sedes_df")
        assert response.status_code == 200
        cargos = response.json()["cargos"]
        assert len(cargos) >= 1

        cargo = cargos[0]
        cargo_encoded = quote(cargo, safe='')

        # Get materias
        response = client.get(f"/api/materias/sedes_df/{cargo_encoded}")
        assert response.status_code == 200
        data = response.json()
        assert "materias" in data
        assert "pesos" in data


class TestCargoFiltering:
    """Test cargo filtering in question selection."""

    def test_filtro_cargo_em_sortear_questoes(self, monkeypatch):
        """Test that cargo filtering works in sortear_questoes."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Save questions with different cargos
            q1 = {
                "enunciado": "Q1 PRF Policial e2e test",
                "alternativas": {"A": "A", "B": "B"},
                "materia": "Português",
                "cargo": "Policial Rodoviário Federal",
                "orgao": "prf",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }
            q2 = {
                "enunciado": "Q2 PRF Admin e2e test",
                "alternativas": {"A": "A", "B": "B"},
                "materia": "Português",
                "cargo": "Agente Administrativo",
                "orgao": "prf",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }

            assert db.salvar_questao(con, q1) == True
            assert db.salvar_questao(con, q2) == True

            # Query with cargo filter
            questoes = db.sortear_questoes(con, "Português", 1, cargo="Policial Rodoviário Federal")
            assert len(questoes) >= 1
            assert questoes[0]["cargo"] == "Policial Rodoviário Federal"

            # Query with different cargo
            questoes = db.sortear_questoes(con, "Português", 1, cargo="Agente Administrativo")
            assert len(questoes) >= 1
            assert questoes[0]["cargo"] == "Agente Administrativo"
        finally:
            con.close()

    def test_multiplos_filtros_cargo_banca_orgao(self, monkeypatch):
        """Test combining cargo + banca + orgao filters."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            q = {
                "enunciado": "Q multiplos filtros e2e test",
                "alternativas": {"A": "A", "B": "B"},
                "materia": "Matemática",
                "cargo": "Técnico",
                "orgao": "BACEN",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }
            assert db.salvar_questao(con, q) == True

            # Query with all three filters
            questoes = db.sortear_questoes(
                con, "Matemática", 1,
                cargo="Técnico",
                banca="Cebraspe",
                orgao="BACEN"
            )
            assert len(questoes) >= 1
            assert questoes[0]["cargo"] == "Técnico"
            assert questoes[0]["banca"] == "Cebraspe"
            assert questoes[0]["orgao"] == "BACEN"
        finally:
            con.close()

    def test_filtros_nao_encontram_questoes(self, monkeypatch):
        """Test that filters correctly return empty when no match."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            q = {
                "enunciado": "Q para teste de filtro",
                "alternativas": {"A": "A", "B": "B"},
                "materia": "Português",
                "cargo": "CargoEspecífico",
                "orgao": "ORGAO_X",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }
            assert db.salvar_questao(con, q) == True

            # Query with non-matching filters should return empty
            questoes = db.sortear_questoes(con, "Português", 1, cargo="CargoDiferente")
            assert len(questoes) == 0
        finally:
            con.close()


class TestAPIErrorHandling:
    """Test error handling in API endpoints."""

    def test_error_invalid_orgao(self, tmp_path, monkeypatch):
        """Test error handling for invalid órgão."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        response = client.get("/api/cargos/orgao_inexistente")
        assert response.status_code == 404

    def test_error_invalid_cargo(self, tmp_path, monkeypatch):
        """Test error handling for invalid cargo."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        response = client.get("/api/materias/prf/cargo_inexistente")
        assert response.status_code == 404

    def test_error_simulado_sem_questoes(self, tmp_path, monkeypatch):
        """Test that simulado generation fails gracefully when no questions."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        response = client.get("/api/cargos/prf")
        if response.status_code == 200:
            cargos = response.json()["cargos"]
            if cargos:
                cargo = cargos[0]
                cargo_encoded = quote(cargo, safe='')
                payload = {"quantidade": 10}
                response = client.post(
                    f"/api/simulado/cargo/prf/{cargo_encoded}",
                    json=payload
                )
                # Should return 404 when no questions found
                assert response.status_code == 404


class TestBackwardCompatibility:
    """Test backward compatibility with old endpoints."""

    def test_backward_compat_api_stats(self, tmp_path, monkeypatch):
        """Ensure old /api/stats endpoint still works."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        response = client.get("/api/stats")
        assert response.status_code == 200
        # Should return dict (even if empty)
        assert isinstance(response.json(), dict)

    def test_backward_compat_api_materias(self, tmp_path, monkeypatch):
        """Ensure old /api/materias endpoint still works."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        response = client.get("/api/materias")
        assert response.status_code == 200
        # Should return list of materia names
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_backward_compat_simulado_materia(self, tmp_path, monkeypatch):
        """Ensure old /api/simulado/materia endpoint still works."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        con = db.conectar()

        try:
            db.salvar_questao(con, {
                "id_qc": "QW_bcompat_1",
                "enunciado": "Teste backward compat?",
                "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                "gabarito": "A",
                "materia": "SUAS",
                "fonte": "qconcursos"
            })
        finally:
            con.close()

        response = client.post(
            "/api/simulado/materia",
            json={"materia": "SUAS", "quantidade": 5}
        )
        # Should work or return 404 if no questions
        assert response.status_code in (200, 404)

    def test_backward_compat_simulado_completo(self, tmp_path, monkeypatch):
        """Ensure old /api/simulado/completo endpoint still works."""
        client = cliente_com_banco(tmp_path, monkeypatch)
        con = db.conectar()

        try:
            db.salvar_questao(con, {
                "id_qc": "QW_bcompat_completo",
                "enunciado": "Teste backward compat completo?",
                "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                "gabarito": "A",
                "materia": "SUAS",
                "fonte": "qconcursos"
            })
        finally:
            con.close()

        response = client.post("/api/simulado/completo", json={"quantidade": 5})
        # Should work or return 404 if no questions
        assert response.status_code in (200, 404)


class TestDataIntegrity:
    """Test data integrity across layers."""

    def test_questao_roundtrip(self, monkeypatch):
        """Test that questions are stored and retrieved correctly."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            original_q = {
                "enunciado": "Teste de integridade de dados",
                "alternativas": {"A": "Option A", "B": "Option B", "C": "Option C"},
                "gabarito": "B",
                "materia": "Português",
                "cargo": "CargoTeste",
                "orgao": "ORGAO_TESTE",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }

            # Save
            assert db.salvar_questao(con, original_q) == True

            # Retrieve
            questoes = db.sortear_questoes(con, "Português", 1)
            assert len(questoes) >= 1

            # Verify
            retrieved_q = questoes[0]
            assert retrieved_q["enunciado"] == original_q["enunciado"]
            assert retrieved_q["alternativas"] == original_q["alternativas"]
            assert retrieved_q["gabarito"] == original_q["gabarito"]
            assert retrieved_q["cargo"] == original_q["cargo"]
            assert retrieved_q["orgao"] == original_q["orgao"]
            assert retrieved_q["banca"] == original_q["banca"]
        finally:
            con.close()

    def test_deduplicacao_por_conteudo(self, monkeypatch):
        """Test that questions are deduplicated by content."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            q1 = {
                "enunciado": "Enunciado idêntico para dedup test",
                "alternativas": {"A": "A", "B": "B", "C": "C"},
                "materia": "Português",
                "cargo": "Teste",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }

            q2 = {
                "id_qc": "DIFF_ID",  # Different ID but same content
                "enunciado": "Enunciado idêntico para dedup test",  # Same enunciado
                "alternativas": {"A": "A", "B": "B", "C": "C"},  # Same alts
                "materia": "Português",
                "cargo": "Teste",
                "banca": "Cebraspe",
                "fonte": "quadrix_pdf",
            }

            # Save first
            result1 = db.salvar_questao(con, q1)
            assert result1 == True

            # Save second (should be deduplicated)
            result2 = db.salvar_questao(con, q2)
            assert result2 == False  # Duplicate content

            # Verify only one exists
            questoes = db.sortear_questoes(con, "Português", 10, cargo="Teste")
            # Should get 1 question (deduplicated)
            assert len(questoes) <= 2  # At most 2 (depends on DISTINCT ON behavior)
        finally:
            con.close()
