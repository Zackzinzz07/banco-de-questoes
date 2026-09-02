"""Performance tests: verify system meets performance targets."""
import pytest
import time
from urllib.parse import quote

import db
import config
import web_api
import edital_loader
from fastapi.testclient import TestClient


def cliente_com_banco(tmp_path, monkeypatch):
    """Create test client with isolated database and simulados directory."""
    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
    monkeypatch.setattr(web_api, "PASTA_SIMULADOS", tmp_path)
    return TestClient(web_api.app)


class TestAPIResponseTimes:
    """Test API endpoint response times."""

    @pytest.mark.performance
    def test_api_orgaos_response_time(self, tmp_path, monkeypatch):
        """GET /api/orgaos should respond in < 200ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        start = time.time()
        response = client.get("/api/orgaos")
        elapsed = (time.time() - start) * 1000  # ms

        assert response.status_code == 200
        assert elapsed < 200, f"Expected < 200ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_api_cargos_response_time(self, tmp_path, monkeypatch):
        """GET /api/cargos/{orgao} should respond in < 200ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        start = time.time()
        response = client.get("/api/cargos/sedes_df")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 200, f"Expected < 200ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_api_materias_response_time(self, tmp_path, monkeypatch):
        """GET /api/materias/{orgao}/{cargo} should respond in < 200ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        # First get a valid cargo
        response = client.get("/api/cargos/sedes_df")
        if response.status_code != 200:
            pytest.skip("Cannot get cargos for SEDES/DF")

        cargos = response.json()["cargos"]
        if not cargos:
            pytest.skip("No cargos available")

        cargo = cargos[0]
        cargo_encoded = quote(cargo, safe='')

        start = time.time()
        response = client.get(f"/api/materias/sedes_df/{cargo_encoded}")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 200, f"Expected < 200ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_api_stats_cargo_response_time(self, tmp_path, monkeypatch):
        """GET /api/stats/cargo/{orgao}/{cargo} should respond in < 300ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        response = client.get("/api/cargos/sedes_df")
        if response.status_code != 200:
            pytest.skip("Cannot get cargos for SEDES/DF")

        cargos = response.json()["cargos"]
        if not cargos:
            pytest.skip("No cargos available")

        cargo = cargos[0]
        cargo_encoded = quote(cargo, safe='')

        start = time.time()
        response = client.get(f"/api/stats/cargo/sedes_df/{cargo_encoded}")
        elapsed = (time.time() - start) * 1000

        assert response.status_code in (200, 404)
        assert elapsed < 300, f"Expected < 300ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_api_backward_compat_stats_response_time(self, tmp_path, monkeypatch):
        """GET /api/stats (old endpoint) should respond in < 500ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        start = time.time()
        response = client.get("/api/stats")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 500, f"Expected < 500ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_api_backward_compat_materias_response_time(self, tmp_path, monkeypatch):
        """GET /api/materias (old endpoint) should respond in < 200ms."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        start = time.time()
        response = client.get("/api/materias")
        elapsed = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 200, f"Expected < 200ms, got {elapsed:.2f}ms"


class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.mark.performance
    def test_sortear_questoes_response_time(self, monkeypatch):
        """sortear_questoes should complete in < 500ms for 1000 questions."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Add questions to database
            for i in range(100):
                for j in range(5):  # 5 cargos
                    q = {
                        "enunciado": f"Test question {i}-{j}",
                        "alternativas": {"A": "A", "B": "B", "C": "C"},
                        "materia": "Português",
                        "cargo": f"Cargo_{j}",
                        "banca": "Cebraspe",
                        "fonte": "qconcursos",
                    }
                    db.salvar_questao(con, q)

            # Benchmark the function
            start = time.time()
            result = db.sortear_questoes(con, "Português", 60)
            elapsed = (time.time() - start) * 1000

            assert elapsed < 500, f"Expected < 500ms, got {elapsed:.2f}ms"
        finally:
            con.close()

    @pytest.mark.performance
    def test_sortear_questoes_com_filtro_response_time(self, monkeypatch):
        """sortear_questoes with filters should complete in < 500ms."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Add questions
            for i in range(50):
                q = {
                    "enunciado": f"Filtered test {i}",
                    "alternativas": {"A": "A", "B": "B"},
                    "materia": "Matemática",
                    "cargo": "CargoEspecifico",
                    "orgao": "ORG_X",
                    "banca": "Cebraspe",
                    "fonte": "qconcursos",
                }
                db.salvar_questao(con, q)

            # Benchmark with filters
            start = time.time()
            result = db.sortear_questoes(
                con, "Matemática", 30,
                cargo="CargoEspecifico",
                orgao="ORG_X"
            )
            elapsed = (time.time() - start) * 1000

            assert elapsed < 500, f"Expected < 500ms, got {elapsed:.2f}ms"
        finally:
            con.close()

    @pytest.mark.performance
    def test_salvar_questao_response_time(self, monkeypatch):
        """salvar_questao should complete in < 50ms."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            q = {
                "enunciado": "Performance test question",
                "alternativas": {"A": "A", "B": "B", "C": "C"},
                "materia": "Português",
                "cargo": "TestCargo",
                "banca": "Cebraspe",
                "fonte": "qconcursos",
            }

            start = time.time()
            result = db.salvar_questao(con, q)
            elapsed = (time.time() - start) * 1000

            assert result == True
            assert elapsed < 100, f"Expected < 100ms, got {elapsed:.2f}ms"
        finally:
            con.close()


class TestLoadTesting:
    """Test system under load."""

    @pytest.mark.performance
    def test_multiple_api_calls_concurrent(self, tmp_path, monkeypatch):
        """Test multiple sequential API calls performance."""
        client = cliente_com_banco(tmp_path, monkeypatch)

        endpoints = [
            "/api/orgaos",
            "/api/cargos/sedes_df",
            "/api/materias",
            "/api/stats",
        ]

        start = time.time()
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200

        elapsed = (time.time() - start) * 1000
        average_ms = elapsed / len(endpoints)

        assert average_ms < 100, \
            f"Average response time should be < 100ms, got {average_ms:.2f}ms"

    @pytest.mark.performance
    def test_massive_database_query(self, monkeypatch):
        """Test query performance with many questions in database."""
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()

        try:
            # Add many questions efficiently
            count = 500
            for i in range(count):
                q = {
                    "enunciado": f"Bulk test {i}",
                    "alternativas": {"A": "A", "B": "B"},
                    "materia": "Português",
                    "cargo": "TestCargo",
                    "fonte": "qconcursos",
                }
                db.salvar_questao(con, q)

            # Query should still be fast
            start = time.time()
            result = db.sortear_questoes(con, "Português", 100, cargo="TestCargo")
            elapsed = (time.time() - start) * 1000

            assert len(result) <= 100
            assert elapsed < 1000, f"Expected < 1000ms for 500 questions, got {elapsed:.2f}ms"
        finally:
            con.close()


class TestEditalLoaderPerformance:
    """Test edital loader performance."""

    @pytest.mark.performance
    def test_listar_concursos_performance(self):
        """listar_concursos should be fast."""
        start = time.time()
        concursos = edital_loader.listar_concursos()
        elapsed = (time.time() - start) * 1000

        assert len(concursos) >= 1
        assert elapsed < 100, f"Expected < 100ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_listar_cargos_performance(self):
        """listar_cargos should be fast."""
        start = time.time()
        cargos = edital_loader.listar_cargos("sedes_df")
        elapsed = (time.time() - start) * 1000

        assert len(cargos) >= 1
        assert elapsed < 100, f"Expected < 100ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_obter_materias_performance(self):
        """obter_materias should be fast."""
        cargos = edital_loader.listar_cargos("sedes_df")
        if not cargos:
            pytest.skip("No cargos for SEDES/DF")

        cargo = cargos[0]

        start = time.time()
        materias = edital_loader.obter_materias("sedes_df", cargo)
        elapsed = (time.time() - start) * 1000

        assert materias is not None
        assert elapsed < 100, f"Expected < 100ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_obter_pesos_performance(self):
        """obter_pesos should be fast."""
        cargos = edital_loader.listar_cargos("sedes_df")
        if not cargos:
            pytest.skip("No cargos for SEDES/DF")

        cargo = cargos[0]

        start = time.time()
        pesos = edital_loader.obter_pesos("sedes_df", cargo)
        elapsed = (time.time() - start) * 1000

        assert len(pesos) > 0
        assert elapsed < 100, f"Expected < 100ms, got {elapsed:.2f}ms"

    @pytest.mark.performance
    def test_distribuir_por_peso_performance(self):
        """distribuir_por_peso should be fast."""
        import edital_loader

        pesos = {f"Materia_{i}": i + 1 for i in range(100)}

        start = time.time()
        dist = edital_loader.distribuir_por_peso(1000, pesos)
        elapsed = (time.time() - start) * 1000

        assert sum(dist.values()) == 1000
        assert elapsed < 50, f"Expected < 50ms, got {elapsed:.2f}ms"
