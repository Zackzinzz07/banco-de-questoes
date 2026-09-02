"""Testes da importação do SQLite legado (pré-PostgreSQL) para o banco atual."""

import json
import sqlite3

import db
from scripts import importar_sqlite

SCHEMA_LEGADO = """
CREATE TABLE questoes (
    id INTEGER PRIMARY KEY,
    id_qc TEXT,
    enunciado TEXT,
    hash_enunciado TEXT,
    alternativas TEXT,
    gabarito TEXT,
    comentario TEXT,
    materia TEXT,
    assunto TEXT,
    banca TEXT,
    orgao TEXT,
    ano INTEGER,
    prova TEXT,
    fonte TEXT,
    usada_em_simulado INTEGER,
    texto_associado TEXT,
    imagens TEXT
);
"""


def _sqlite_legado(caminho, linhas):
    con = sqlite3.connect(caminho)
    con.executescript(SCHEMA_LEGADO)
    con.executemany(
        "INSERT INTO questoes (id_qc, enunciado, alternativas, gabarito, materia,"
        " assunto, banca, orgao, ano, prova, fonte, texto_associado, imagens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        linhas,
    )
    con.commit()
    con.close()
    return caminho


def test_ler_questoes_converte_json_de_alternativas(tmp_path):
    caminho = _sqlite_legado(
        tmp_path / "legado.db",
        [
            (
                "Q1",
                "Enunciado um?",
                json.dumps({"A": "alt a", "B": "alt b"}),
                "A",
                "Língua Portuguesa",
                "Crase",
                "Cebraspe",
                "PRF",
                2024,
                "prova x",
                "qconcursos",
                "",
                None,
            )
        ],
    )

    questoes = importar_sqlite.ler_questoes(caminho)

    assert len(questoes) == 1
    assert questoes[0]["alternativas"] == {"A": "alt a", "B": "alt b"}
    assert questoes[0]["banca"] == "Cebraspe"
    assert questoes[0]["fonte"] == "qconcursos"


def test_importar_grava_no_postgres_e_conta_duplicadas(tmp_path):
    caminho = _sqlite_legado(
        tmp_path / "legado.db",
        [
            (
                "Q1",
                "Enunciado um?",
                json.dumps({"A": "a", "B": "b"}),
                "A",
                "Língua Portuguesa",
                None,
                "Cebraspe",
                "PRF",
                2024,
                None,
                "qconcursos",
                None,
                None,
            ),
            (
                "Q2",
                "Enunciado dois?",
                json.dumps({"A": "a", "B": "b"}),
                "B",
                "SUAS",
                None,
                "Instituto Quadrix",
                "SEDES/DF",
                2026,
                None,
                "quadrix_pdf",
                None,
                None,
            ),
        ],
    )
    con = db.conectar()

    importadas, duplicadas = importar_sqlite.importar(importar_sqlite.ler_questoes(caminho), con)

    assert (importadas, duplicadas) == (2, 0)
    linha = con.execute("SELECT banca, orgao, ano, fonte FROM questoes WHERE id_qc='Q1'").fetchone()
    assert (linha["banca"], linha["orgao"], linha["ano"], linha["fonte"]) == (
        "Cebraspe",
        "PRF",
        2024,
        "qconcursos",
    )

    # Rodar de novo não duplica — o dedupe por content_hash barra.
    de_novo = importar_sqlite.importar(importar_sqlite.ler_questoes(caminho), con)
    assert de_novo == (0, 2)
    con.close()


def test_importar_ignora_questao_sem_enunciado_ou_alternativas(tmp_path):
    caminho = _sqlite_legado(
        tmp_path / "legado.db",
        [
            (
                "Q1",
                "",
                json.dumps({"A": "a"}),
                "A",
                "SUAS",
                None,
                None,
                None,
                2026,
                None,
                "qconcursos",
                None,
                None,
            ),
            (
                "Q2",
                "Tem enunciado mas sem alternativas?",
                json.dumps({}),
                "A",
                "SUAS",
                None,
                None,
                None,
                2026,
                None,
                "qconcursos",
                None,
                None,
            ),
        ],
    )

    questoes = importar_sqlite.ler_questoes(caminho)

    assert questoes == []
