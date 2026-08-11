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
    fonte TEXT NOT NULL CHECK (fonte IN ('qconcursos', 'quadrix_pdf')),
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
    fonte = q.get("fonte")
    if fonte not in ("qconcursos", "quadrix_pdf"):
        raise ValueError(f"fonte inválida: '{fonte}'. Use 'qconcursos' ou 'quadrix_pdf'.")

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
                fonte,
            ),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def sortear_questoes(con, materia, quantidade):
    """Sorteia questões não usadas; se faltar, avisa e completa com repetidas."""
    linhas = con.execute(
        "SELECT * FROM questoes WHERE materia=? AND usada_em_simulado=0"
        " ORDER BY RANDOM() LIMIT ?", (materia, quantidade)).fetchall()
    questoes = [dict(l) for l in linhas]
    faltam = quantidade - len(questoes)
    if faltam > 0:
        repetidas = con.execute(
            "SELECT * FROM questoes WHERE materia=? AND usada_em_simulado=1"
            " ORDER BY RANDOM() LIMIT ?", (materia, faltam)).fetchall()
        if repetidas:
            print(f"Aviso: só {len(questoes)} questões inéditas de {materia};"
                  f" completando com {len(repetidas)} repetidas.")
        questoes += [dict(l) for l in repetidas]
    for q in questoes:
        q["alternativas"] = json.loads(q["alternativas"])
    return questoes


def marcar_usadas(con, ids):
    con.executemany("UPDATE questoes SET usada_em_simulado=1 WHERE id=?",
                    [(i,) for i in ids])
    con.commit()


def zerar_usadas(con):
    con.execute("UPDATE questoes SET usada_em_simulado=0")
    con.commit()


def obter_progresso(con, materia):
    linha = con.execute("SELECT ultima_pagina FROM progresso_scraper WHERE materia=?",
                        (materia,)).fetchone()
    return linha["ultima_pagina"] if linha else 0


def salvar_progresso(con, materia, pagina):
    con.execute(
        "INSERT INTO progresso_scraper (materia, ultima_pagina) VALUES (?,?)"
        " ON CONFLICT(materia) DO UPDATE SET ultima_pagina=excluded.ultima_pagina",
        (materia, pagina))
    con.commit()


def sem_gabarito(con):
    linhas = con.execute(
        "SELECT * FROM questoes WHERE gabarito IS NULL AND id_qc IS NOT NULL").fetchall()
    return [dict(l) for l in linhas]


def atualizar_gabarito(con, id_qc, gabarito, comentario=None):
    con.execute("UPDATE questoes SET gabarito=?, comentario=? WHERE id_qc=?",
                (gabarito, comentario, id_qc))
    con.commit()
