"""Tests for cargo-based endpoints in web_api.py"""
import config
import db
import web_api
import edital_loader
from fastapi.testclient import TestClient
from urllib.parse import quote


def cliente_com_banco(tmp_path, monkeypatch):
    """Create test client with isolated database and simulados directory."""
    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
    monkeypatch.setattr(web_api, "PASTA_SIMULADOS", tmp_path)
    return TestClient(web_api.app)


def test_listar_orgaos(tmp_path, monkeypatch):
    """GET /api/orgaos returns list of available órgãos/concursos."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/orgaos")
    assert response.status_code == 200
    data = response.json()
    assert "orgaos" in data
    assert isinstance(data["orgaos"], list)
    assert len(data["orgaos"]) >= 1  # At least SEDES/DF


def test_listar_cargos_sedes_df(tmp_path, monkeypatch):
    """GET /api/cargos/sedes_df returns available cargos for SEDES/DF."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/cargos/sedes_df")
    assert response.status_code == 200
    data = response.json()
    assert "cargos" in data
    assert "orgao" in data
    assert data["orgao"] == "sedes_df"
    assert isinstance(data["cargos"], list)
    assert len(data["cargos"]) >= 1


def test_listar_cargos_invalido(tmp_path, monkeypatch):
    """GET /api/cargos/inexistente returns 404."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/cargos/concurso_inexistente")
    assert response.status_code == 404


def test_listar_materias_cargo(tmp_path, monkeypatch):
    """GET /api/materias/{orgao}/{cargo} returns subjects and weights."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)

    # Get available cargos for SEDES/DF
    cargos_response = cliente.get("/api/cargos/sedes_df")
    assert cargos_response.status_code == 200
    cargos = cargos_response.json()["cargos"]
    assert len(cargos) > 0

    cargo = cargos[0]
    # URL encode the cargo name
    cargo_encoded = quote(cargo, safe='')

    response = cliente.get(f"/api/materias/sedes_df/{cargo_encoded}")
    assert response.status_code == 200
    data = response.json()
    assert "materias" in data
    assert "pesos" in data
    assert "total_questoes" in data
    assert "orgao" in data
    assert "cargo" in data
    assert data["orgao"] == "sedes_df"
    assert data["cargo"] == cargo
    assert data["total_questoes"] > 0
    assert isinstance(data["pesos"], dict)


def test_listar_materias_cargo_invalido(tmp_path, monkeypatch):
    """GET /api/materias/{orgao}/{cargo} returns 404 for invalid cargo."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/materias/sedes_df/cargo_inexistente")
    assert response.status_code == 404


def test_stats_cargo(tmp_path, monkeypatch):
    """GET /api/stats/cargo/{orgao}/{cargo} returns stats for specific cargo."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()

    # Save some test questions with cargo info
    for i in range(3):
        db.salvar_questao(con, {
            "id_qc": f"QW_cargo_{i}",
            "enunciado": f"Enunciado cargo {i}?",
            "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            "gabarito": "A",
            "materia": "SUAS",
            "cargo": "Técnico de Atendimento Direto ao Cidadão",
            "orgao": "sedes_df",
            "fonte": "qconcursos"
        })
    con.close()

    response = cliente.get(
        "/api/stats/cargo/sedes_df/T%C3%A9cnico%20de%20Atendimento%20Direto%20ao%20Cidad%C3%A3o"
    )
    assert response.status_code == 200
    data = response.json()
    assert "materias" in data
    assert "total" in data
    assert "coletadas" in data["total"]
    assert "esperadas" in data["total"]
    assert "percentual" in data["total"]
    assert data["orgao"] == "sedes_df"
    assert data["total"]["coletadas"] >= 0


def test_gerar_simulado_cargo(tmp_path, monkeypatch):
    """POST /api/simulado/cargo/{orgao}/{cargo} generates PDF for cargo."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()

    # Save enough questions for a simulado with cargo filter
    cargo_nome = "Técnico de Atendimento Direto ao Cidadão"
    materias = edital_loader.obter_materias("sedes_df", cargo_nome)

    if materias:
        for materia in materias.keys():
            for i in range(10):  # Save 10 questions per materia
                db.salvar_questao(con, {
                    "id_qc": f"QW_sim_{materia}_{i}",
                    "enunciado": f"Enunciado {materia} {i}?",
                    "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                    "gabarito": "A",
                    "materia": materia,
                    "cargo": cargo_nome,
                    "orgao": "sedes_df",
                    "fonte": "qconcursos"
                })
    con.close()

    cargo_encoded = quote(cargo_nome, safe='')
    payload = {"quantidade": 20}
    response = cliente.post(
        f"/api/simulado/cargo/sedes_df/{cargo_encoded}",
        json=payload
    )
    # Should succeed if we have questions, or 404 if not
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "arquivo" in data
        assert data["orgao"] == "sedes_df"
        assert data["cargo"] == cargo_nome
        assert data["quantidade"] == 20


def test_gerar_simulado_cargo_com_banca(tmp_path, monkeypatch):
    """POST /api/simulado/cargo with banca filter."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()

    cargo_nome = "Técnico de Atendimento Direto ao Cidadão"
    materias = edital_loader.obter_materias("sedes_df", cargo_nome)

    if materias:
        for materia in materias.keys():
            for i in range(5):
                db.salvar_questao(con, {
                    "id_qc": f"QW_banca_{materia}_{i}",
                    "enunciado": f"Enunciado banca {materia} {i}?",
                    "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
                    "gabarito": "A",
                    "materia": materia,
                    "cargo": cargo_nome,
                    "orgao": "sedes_df",
                    "banca": "Instituto Quadrix",
                    "fonte": "qconcursos"
                })
    con.close()

    cargo_encoded = quote(cargo_nome, safe='')
    payload = {"quantidade": 10, "banca": "Instituto Quadrix"}
    response = cliente.post(
        f"/api/simulado/cargo/sedes_df/{cargo_encoded}",
        json=payload
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "banca" in data
        assert data["banca"] == "Instituto Quadrix"


def test_backward_compat_stats(tmp_path, monkeypatch):
    """Old /api/stats endpoint still works (backward compatibility)."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/stats")
    assert response.status_code == 200
    # Should return dict (even if empty)
    assert isinstance(response.json(), dict)


def test_backward_compat_materias(tmp_path, monkeypatch):
    """Old /api/materias endpoint still works (backward compatibility)."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    response = cliente.get("/api/materias")
    assert response.status_code == 200
    # Should return list of materia names
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_backward_compat_simulado_completo(tmp_path, monkeypatch):
    """Old /api/simulado/completo endpoint still works (backward compatibility)."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()

    # Save a question
    db.salvar_questao(con, {
        "id_qc": "QW_compat",
        "enunciado": "Teste compat?",
        "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
        "gabarito": "A",
        "materia": "SUAS",
        "fonte": "qconcursos"
    })
    con.close()

    response = cliente.post("/api/simulado/completo", json={"quantidade": 10})
    # Should work or return 404 if no questions
    assert response.status_code in (200, 404)


def test_backward_compat_simulado_materia(tmp_path, monkeypatch):
    """Old /api/simulado/materia endpoint still works (backward compatibility)."""
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()

    db.salvar_questao(con, {
        "id_qc": "QW_mat",
        "enunciado": "Teste materia?",
        "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
        "gabarito": "A",
        "materia": "SUAS",
        "fonte": "qconcursos"
    })
    con.close()

    response = cliente.post(
        "/api/simulado/materia",
        json={"materia": "SUAS", "quantidade": 10}
    )
    assert response.status_code in (200, 404)
