"""Banco PostgreSQL de questões: conexão, criação de tabelas, salvar com dedupe."""
import hashlib
import json
import re

import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor

import config

DATABASE_URL = config.DATABASE_URL

FONTES_VALIDAS = {"qconcursos", "quadrix_pdf", "pci"}

SQL_CRIAR = """
CREATE TABLE IF NOT EXISTS questoes (
    id SERIAL PRIMARY KEY,
    id_qc TEXT UNIQUE,
    enunciado TEXT NOT NULL,
    hash_enunciado TEXT UNIQUE NOT NULL,
    content_hash TEXT,
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
    usada_em_simulado INTEGER NOT NULL DEFAULT 0,
    texto_associado TEXT,
    imagens TEXT
);
CREATE INDEX IF NOT EXISTS idx_questoes_materia_usada ON questoes(materia, usada_em_simulado);
CREATE INDEX IF NOT EXISTS idx_questoes_fonte ON questoes(fonte);
CREATE INDEX IF NOT EXISTS idx_questoes_content_hash ON questoes(content_hash);
CREATE TABLE IF NOT EXISTS progresso_scraper (
    fonte TEXT NOT NULL,
    chave TEXT NOT NULL,
    ultima_pagina INTEGER NOT NULL,
    PRIMARY KEY (fonte, chave)
);
"""


class _Conexao:
    """Wrapper fino sobre a conexão psycopg2, para manter a API antiga do
    sqlite3.Connection usada em todo o código (con.execute(...).fetchone()/
    fetchall(), con.executemany(...), con.commit(), con.close()).

    Cursores usam RealDictCursor (herdado do cursor_factory da conexão), então
    as linhas suportam dict(linha) e linha["coluna"] como o sqlite3.Row antigo.
    """

    def __init__(self, con):
        self._con = con

    def execute(self, sql, params=None):
        cur = self._con.cursor()
        cur.execute(sql, params or None)
        return cur

    def executemany(self, sql, params_list):
        cur = self._con.cursor()
        cur.executemany(sql, params_list)
        return cur

    def cursor(self, *args, **kwargs):
        return self._con.cursor(*args, **kwargs)

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        self._con.close()


def conectar(caminho=None):
    """Abre conexão com o PostgreSQL e garante que as tabelas existam.

    `caminho` é um parâmetro legado (do tempo do SQLite) mantido só por
    compatibilidade retroativa com chamadas existentes; é ignorado — a
    conexão sempre usa `DATABASE_URL` (de config.py).
    """
    con = _Conexao(psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor))
    con.execute(SQL_CRIAR)
    con.commit()
    return con


def normalizar_enunciado(texto):
    return re.sub(r"\s+", " ", texto).strip().lower()


def hash_enunciado(texto):
    return hashlib.sha256(normalizar_enunciado(texto).encode("utf-8")).hexdigest()


def content_hash(enunciado, alternativas):
    """MD5 de enunciado + alternativas serializadas para dedupe rápido."""
    content = normalizar_enunciado(enunciado) + "|" + json.dumps(alternativas, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def salvar_questao(con, q):
    """Insere a questão; retorna True se inseriu, False se já existia (dedupe)."""
    fonte = q.get("fonte")
    if fonte not in FONTES_VALIDAS:
        raise ValueError(f"fonte inválida: '{fonte}'. Use {', '.join(sorted(FONTES_VALIDAS))}.")

    try:
        con.execute(
            "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, content_hash, alternativas,"
            " gabarito, comentario, materia, assunto, banca, orgao, ano, prova, fonte,"
            " texto_associado, imagens)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                q.get("id_qc"),
                q["enunciado"],
                hash_enunciado(q["enunciado"]),
                content_hash(q["enunciado"], q["alternativas"]),
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
                q.get("texto_associado"),
                json.dumps(q["imagens"], ensure_ascii=False) if q.get("imagens") else None,
            ),
        )
        con.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        con.rollback()  # CRITICAL: evita "current transaction is aborted"
        return False


def sortear_questoes(con, materia, quantidade):
    """Sorteia questões não usadas (deduplicadas por conteúdo); se faltar, avisa e completa com repetidas."""
    linhas = con.execute(
        "SELECT DISTINCT ON (content_hash) * FROM questoes"
        " WHERE materia=%s AND usada_em_simulado=0 AND content_hash IS NOT NULL"
        " ORDER BY content_hash,"
        "   CASE fonte WHEN 'qconcursos' THEN 1 WHEN 'pci' THEN 2 ELSE 3 END,"
        "   RANDOM() LIMIT %s", (materia, quantidade)).fetchall()
    questoes = [dict(l) for l in linhas]
    faltam = quantidade - len(questoes)
    if faltam > 0:
        repetidas = con.execute(
            "SELECT DISTINCT ON (content_hash) * FROM questoes"
            " WHERE materia=%s AND usada_em_simulado=1 AND content_hash IS NOT NULL"
            " ORDER BY content_hash,"
            "   CASE fonte WHEN 'qconcursos' THEN 1 WHEN 'pci' THEN 2 ELSE 3 END,"
            "   RANDOM() LIMIT %s", (materia, faltam)).fetchall()
        if repetidas:
            print(f"Aviso: só {len(questoes)} questões inéditas de {materia};"
                  f" completando com {len(repetidas)} repetidas.")
        questoes += [dict(l) for l in repetidas]
    for q in questoes:
        q["alternativas"] = json.loads(q["alternativas"])
        q["imagens"] = json.loads(q["imagens"]) if q["imagens"] else []
    return questoes


def marcar_usadas(con, ids):
    con.executemany("UPDATE questoes SET usada_em_simulado=1 WHERE id=%s",
                    [(i,) for i in ids])
    con.commit()


def zerar_usadas(con):
    con.execute("UPDATE questoes SET usada_em_simulado=0")
    con.commit()


def obter_progresso(con, fonte, chave):
    linha = con.execute(
        "SELECT ultima_pagina FROM progresso_scraper WHERE fonte=%s AND chave=%s",
        (fonte, chave)).fetchone()
    return linha["ultima_pagina"] if linha else 0


def salvar_progresso(con, fonte, chave, pagina):
    con.execute(
        "INSERT INTO progresso_scraper (fonte, chave, ultima_pagina) VALUES (%s,%s,%s)"
        " ON CONFLICT (fonte, chave) DO UPDATE SET ultima_pagina=excluded.ultima_pagina",
        (fonte, chave, pagina))
    con.commit()


def sem_gabarito(con):
    linhas = con.execute(
        "SELECT * FROM questoes WHERE gabarito IS NULL AND id_qc IS NOT NULL").fetchall()
    return [dict(l) for l in linhas]


def atualizar_gabarito(con, id_qc, gabarito, comentario=None):
    con.execute("UPDATE questoes SET gabarito=%s, comentario=%s WHERE id_qc=%s",
                (gabarito, comentario, id_qc))
    con.commit()


def completar_texto_associado(con, id_qc, texto, imagens):
    """Preenche texto/imagens de uma questão já salva que ainda não os tinha."""
    if not id_qc or (not texto and not imagens):
        return False
    cur = con.execute(
        "UPDATE questoes SET texto_associado=%s, imagens=%s WHERE id_qc=%s"
        " AND (texto_associado IS NULL OR texto_associado='')"
        " AND (imagens IS NULL OR imagens='')",
        (texto or None, json.dumps(imagens, ensure_ascii=False) if imagens else None,
         id_qc))
    con.commit()
    return cur.rowcount > 0


def estatisticas(con):
    """Por matéria: total, inéditas, usadas e sem gabarito."""
    linhas = con.execute(
        "SELECT materia, COUNT(*) total,"
        " SUM(CASE WHEN usada_em_simulado=0 THEN 1 ELSE 0 END) ineditas,"
        " SUM(usada_em_simulado) usadas,"
        " SUM(CASE WHEN gabarito IS NULL THEN 1 ELSE 0 END) sem_gabarito"
        " FROM questoes GROUP BY materia ORDER BY materia").fetchall()
    return {l["materia"]: {"total": l["total"], "ineditas": l["ineditas"],
                           "usadas": l["usadas"], "sem_gabarito": l["sem_gabarito"]}
            for l in linhas}
