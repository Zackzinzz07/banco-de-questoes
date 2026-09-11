"""Banco PostgreSQL de questões: conexão, criação de tabelas, salvar com dedupe."""

import hashlib
import json
import re

import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor

import sanitizacao

try:
    from . import config
except ImportError:
    import config

DATABASE_URL = config.DATABASE_URL

FONTES_VALIDAS = {"qconcursos", "quadrix_pdf", "pci", "cebraspe"}

# As migrations usam ALTER TABLE, que pede AccessExclusiveLock na tabela
# inteira mesmo com IF NOT EXISTS. Reaplicar isso a cada conectar() enfileira
# locks quando o processo tem mais de uma conexão viva (era o que travava a
# suíte de testes). Rodam uma vez por processo.
_MIGRACOES_APLICADAS = False

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
    ano INTEGER,
    prova TEXT,
    fonte TEXT NOT NULL,
    usada_em_simulado INTEGER NOT NULL DEFAULT 0,
    texto_associado TEXT,
    imagens TEXT,
    categoria VARCHAR(255),
    tema VARCHAR(255),
    imagens_urls JSONB DEFAULT '[]'::jsonb
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
    global _MIGRACOES_APLICADAS

    con = _Conexao(psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor))
    # Sem autocommit, um SELECT solto deixa a transação aberta até alguém
    # commitar/fechar; conexão esquecida assim segura lock e trava o próximo
    # ALTER TABLE/TRUNCATE indefinidamente.
    con._con.autocommit = True
    con.execute(SQL_CRIAR)

    if not _MIGRACOES_APLICADAS:
        try:
            from migrations import migration_001, migration_002, migration_003

            migration_001.aplicar(con)
            migration_002.aplicar(con)
            migration_003.aplicar(con)
            _MIGRACOES_APLICADAS = True
        except ImportError:
            pass  # Migrations not available (should not happen in normal use)

    return con


def normalizar_enunciado(texto):
    return re.sub(r"\s+", " ", texto).strip().lower()


def hash_enunciado(texto):
    return hashlib.sha256(normalizar_enunciado(texto).encode("utf-8")).hexdigest()


def content_hash(enunciado, alternativas):
    """MD5 de enunciado + alternativas serializadas para dedupe rápido."""
    content = (
        normalizar_enunciado(enunciado)
        + "|"
        + json.dumps(alternativas, sort_keys=True, ensure_ascii=False)
    )
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _inferir_formato(alternativas):
    """Sem a chave "D", não é múltipla escolha: C/E não passa de C e E."""
    if not alternativas or "D" not in alternativas:
        return "certo_errado"
    return "multipla_escolha"


def salvar_questao(con, q):
    """Insere a questão; retorna True se inseriu, False se já existia (dedupe por content_hash)."""
    fonte = q.get("fonte")
    if fonte not in FONTES_VALIDAS:
        raise ValueError(f"fonte inválida: '{fonte}'. Use {', '.join(sorted(FONTES_VALIDAS))}.")

    # PostgreSQL rejeita 0x00 em text; limpar aqui protege todas as fontes.
    q = sanitizacao.sem_nul(q)
    c_hash = content_hash(q["enunciado"], q["alternativas"])
    # Gabarito "" é ausência de gabarito, não gabarito válido: guardar a string
    # vazia esconderia a questão de sem_gabarito() para sempre.
    gabarito = (q.get("gabarito") or "").strip() or None

    # Verificar se questão com mesmo conteúdo já existe
    existente = con.execute(
        "SELECT id FROM questoes WHERE content_hash = %s",
        (c_hash,),
    ).fetchone()

    if existente:
        return False  # Questão duplicada, ignora

    formato = q.get("formato") or _inferir_formato(q["alternativas"])

    try:
        con.execute(
            "INSERT INTO questoes (id_qc, enunciado, hash_enunciado, content_hash, alternativas,"
            " gabarito, comentario, materia, assunto, ano, prova, fonte,"
            " texto_associado, imagens, categoria, tema, imagens_urls,"
            " banca, orgao, cargo, formato)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                q.get("id_qc"),
                q["enunciado"],
                hash_enunciado(q["enunciado"]),
                c_hash,
                json.dumps(q["alternativas"], ensure_ascii=False),
                gabarito,
                q.get("comentario"),
                q["materia"],
                q.get("assunto"),
                q.get("ano"),
                q.get("prova"),
                fonte,
                q.get("texto_associado"),
                json.dumps(q["imagens"], ensure_ascii=False) if q.get("imagens") else None,
                q.get("categoria"),
                q.get("tema"),
                json.dumps(q.get("imagens_urls", []), ensure_ascii=False),
                q.get("banca"),
                q.get("orgao"),
                q.get("cargo"),
                formato,
            ),
        )
        con.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        con.rollback()  # CRITICAL: evita "current transaction is aborted"
        return False


# O DISTINCT ON exige que o ORDER BY comece pela sua expressão, então um
# RANDOM() ali dentro nunca sorteia nada: cada content_hash tem uma linha só.
# A subquery deduplica e o sorteio acontece do lado de fora.
_SQL_SORTEIO = (
    "SELECT * FROM ("
    "  SELECT DISTINCT ON (content_hash) * FROM questoes WHERE {onde}"
    "   ORDER BY content_hash,"
    "     CASE fonte WHEN 'cebraspe' THEN 1 WHEN 'qconcursos' THEN 2 WHEN 'pci' THEN 3 ELSE 4 END"
    ") AS unicas ORDER BY RANDOM() LIMIT %s"
)


def _sortear(con, materia, quantidade, usadas, banca, orgao, cargo, formato):
    """Sorteia `quantidade` questões distintas por conteúdo, em ordem aleatória."""
    onde = ["materia=%s", "usada_em_simulado=%s", "content_hash IS NOT NULL"]
    params = [materia, usadas]
    filtros = (("banca", banca), ("orgao", orgao), ("cargo", cargo), ("formato", formato))
    for coluna, valor in filtros:
        if valor:
            if coluna in ("banca", "orgao", "cargo"):
                onde.append(f"{coluna} ILIKE %s")
                params.append(f"%{valor}%")
            else:
                onde.append(f"{coluna}=%s")
                params.append(valor)
    params.append(quantidade)
    sql = _SQL_SORTEIO.format(onde=" AND ".join(onde))
    return [dict(linha) for linha in con.execute(sql, tuple(params)).fetchall()]


def sortear_questoes(con, materia, quantidade, banca=None, orgao=None, cargo=None, formato=None):
    """Sorteia questões inéditas, deduplicadas por conteúdo.

    Se não houver inéditas suficientes, avisa e completa com repetidas.

    Args:
        con: Conexão com o banco
        materia: Matéria/disciplina para filtro
        quantidade: Número de questões desejadas
        banca: Nome da banca examinadora (opcional, ex: "Instituto Quadrix")
        orgao: Órgão/concurso (opcional, ex: "SEDES/DF")
        cargo: Cargo (opcional, ex: "Policial Rodoviário Federal")
        formato: "certo_errado" ou "multipla_escolha" (opcional)
    """
    questoes = _sortear(con, materia, quantidade, 0, banca, orgao, cargo, formato)

    faltam = quantidade - len(questoes)
    if faltam > 0:
        repetidas = _sortear(con, materia, faltam, 1, banca, orgao, cargo, formato)
        if repetidas:
            print(
                f"Aviso: só {len(questoes)} questões inéditas de {materia};"
                f" completando com {len(repetidas)} repetidas."
            )
        questoes += repetidas

    for q in questoes:
        q["alternativas"] = json.loads(q["alternativas"])
        q["imagens"] = json.loads(q["imagens"]) if q["imagens"] else []
    return questoes


def marcar_usadas(con, ids):
    con.executemany("UPDATE questoes SET usada_em_simulado=1 WHERE id=%s", [(i,) for i in ids])
    con.commit()


def zerar_usadas(con):
    con.execute("UPDATE questoes SET usada_em_simulado=0")
    con.commit()


def obter_progresso(con, fonte, chave):
    linha = con.execute(
        "SELECT ultima_pagina FROM progresso_scraper WHERE fonte=%s AND chave=%s", (fonte, chave)
    ).fetchone()
    return linha["ultima_pagina"] if linha else 0


def salvar_progresso(con, fonte, chave, pagina):
    con.execute(
        "INSERT INTO progresso_scraper (fonte, chave, ultima_pagina) VALUES (%s,%s,%s)"
        " ON CONFLICT (fonte, chave) DO UPDATE SET ultima_pagina=excluded.ultima_pagina",
        (fonte, chave, pagina),
    )
    con.commit()


def sem_gabarito(con):
    linhas = con.execute(
        "SELECT * FROM questoes WHERE (gabarito IS NULL OR gabarito = '') AND id_qc IS NOT NULL"
    ).fetchall()
    return [dict(l) for l in linhas]


def atualizar_gabarito(con, id_qc, gabarito, comentario=None):
    con.execute(
        "UPDATE questoes SET gabarito=%s, comentario=%s WHERE id_qc=%s",
        (gabarito, comentario, id_qc),
    )
    con.commit()


def completar_texto_associado(con, id_qc, texto, imagens):
    """Preenche texto/imagens de uma questão já salva que ainda não os tinha."""
    if not id_qc or (not texto and not imagens):
        return False
    cur = con.execute(
        "UPDATE questoes SET texto_associado=%s, imagens=%s WHERE id_qc=%s"
        " AND (texto_associado IS NULL OR texto_associado='')"
        " AND (imagens IS NULL OR imagens='')",
        (texto or None, json.dumps(imagens, ensure_ascii=False) if imagens else None, id_qc),
    )
    con.commit()
    return cur.rowcount > 0


def estatisticas(con):
    """Por matéria: total, inéditas, usadas e sem gabarito."""
    linhas = con.execute(
        "SELECT materia, COUNT(*) total,"
        " SUM(CASE WHEN usada_em_simulado=0 THEN 1 ELSE 0 END) ineditas,"
        " SUM(usada_em_simulado) usadas,"
        " SUM(CASE WHEN gabarito IS NULL OR gabarito = '' THEN 1 ELSE 0 END) sem_gabarito"
        " FROM questoes GROUP BY materia ORDER BY materia"
    ).fetchall()
    return {
        l["materia"]: {
            "total": l["total"],
            "ineditas": l["ineditas"],
            "usadas": l["usadas"],
            "sem_gabarito": l["sem_gabarito"],
        }
        for l in linhas
    }
