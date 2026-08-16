import config
import db
import web_api
from fastapi.testclient import TestClient


def cliente_com_banco(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
    monkeypatch.setattr(web_api, "PASTA_SIMULADOS", tmp_path)
    return TestClient(web_api.app)


def test_stats_vazio(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.get("/api/stats")
    assert r.status_code == 200
    assert r.json() == {}


def test_materias(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    nomes = cliente.get("/api/materias").json()
    assert len(nomes) == 8 and "SUAS" in nomes


def test_simulado_materia_e_download(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    con = db.conectar()
    for i in range(3):
        db.salvar_questao(con, {
            "id_qc": f"QW{i}", "enunciado": f"Enunciado {i}?",
            "alternativas": {"A": "a", "B": "b", "C": "c", "D": "d", "E": "e"},
            "gabarito": "A", "materia": "SUAS", "fonte": "qconcursos"})
    r = cliente.post("/api/simulado/materia", json={"materia": "SUAS", "quantidade": 3})
    assert r.status_code == 200
    nome = r.json()["arquivo"]
    assert nome.endswith(".pdf")
    baixado = cliente.get(f"/api/simulados/download/{nome}")
    assert baixado.status_code == 200
    assert baixado.content[:5] == b"%PDF-"


def test_simulado_materia_banco_vazio_da_404(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.post("/api/simulado/materia", json={"materia": "SUAS", "quantidade": 3})
    assert r.status_code == 404


def test_download_bloqueia_path_traversal(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.get("/api/simulados/download/..%2Fdb.py")
    assert r.status_code in (400, 404)


def test_zerar(tmp_path, monkeypatch):
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    assert cliente.post("/api/simulados/zerar").status_code == 200


def test_coletar_desabilitado(tmp_path, monkeypatch):
    monkeypatch.setattr(web_api, "COLETA_DISPONIVEL", False)
    cliente = cliente_com_banco(tmp_path, monkeypatch)
    r = cliente.post("/api/coletar")
    assert r.status_code == 503
    assert "fora do Docker" in r.json()["detail"]
