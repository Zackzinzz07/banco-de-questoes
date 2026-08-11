"""Banco SQLite de questões: conexão, criação de tabelas, salvar com dedupe."""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ARQUIVO_BANCO = Path(__file__).resolve().parent / "banco_de_questoes.db"

SQL_CRIAR = """
CREATE TABLE IF NOT EXISTS questoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_qc TEXT UNIQUE,
    enunciado TEXT NOT NULL,
    hash_enunciado TEXT UNIQUE NOT NULL,
    alternativas TEXT NOT NULL,
    gabarito TEXT,
    comentario TEXT,
    materia TEXT NOT NULL,
    assunto TEXT,
    banca TEXT,
    orgao TEXT,
    ano INTEGER,
    prova TEXT,
    fonte TEXT NOT NULL,
    usada_em_simulado INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS progresso_scraper (
    materia TEXT PRIMARY KEY,
    ultima_pagina INTEGER NOT NULL
);
"""


def conectar(caminho=None):
    con = sqlite3.connect(caminho or ARQUIVO_BANCO)
    con.row_factory = sqlite3.Row
    con.executescript(SQL_CRIAR)
    return con


def normalizar_enunciado(texto):
    return re.sub(r"\s+", " ", texto).strip().lower()


def hash_enunciado(texto):
    return hashlib.sha256(normalizar_enunciado(texto).encode("utf-8")).hexdigest()


def salvar_questao(con, q):
    """Insere a questão; retorna True se inseriu, False se já existia (dedupe)."""
    try:
        con.execute(
            "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, alternativas,"
            " gabarito, comentario, materia, assunto, banca, orgao, ano, prova, fonte)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                q.get("id_qc"),
                q["enunciado"],
                hash_enunciado(q["enunciado"]),
                json.dumps(q["alternativas"], ensure_ascii=False),
                q.get("gabarito"),
                q.get("comentario"),
                q["materia"],
                q.get("assunto"),
                q.get("banca"),
                q.get("orgao"),
                q.get("ano"),
                q.get("prova"),
                q["fonte"],
            ),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
