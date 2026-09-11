"""Migration: tabelas materias/conteudos, normalizando categoria/tema/assunto.

`categoria`, `tema` e `assunto` são o mesmo conceito -- "tópico dentro da
matéria" -- escritos com três nomes diferentes porque três scrapers
decidiram cada um o seu campo, sem combinar entre si (achado do
cruzamento semântico em `scripts/mapear_conteudo_edital.py`). Esta
migration cria as tabelas normalizadas e faz o backfill inicial a partir
de `categoria`, que é a coluna mais confiável (80-100% preenchida onde a
matéria tem categorização, contra 0-25% de `assunto`).

`questoes.materia` continua sendo texto livre -- não muda aqui. Nome
canônico em `materias` dedupliza variantes que `taxonomia.normalizar()`
já trata como a mesma coisa (ex.: "Informática" e "Noções de
Informática"), usando como nome a variante com mais questões.

`categoria`/`tema`/`assunto` continuam vivas: esta migration só adiciona
`conteudo_id`, não remove nada. Remover as colunas antigas é decisão
separada, para depois de confirmar que nada mais lê delas.

Idempotente: pode ser chamada de novo a qualquer momento para pegar
questões novas que ainda não têm `conteudo_id` -- o backfill só toca
linhas com `conteudo_id IS NULL`.
"""

try:
    from . import taxonomia
except ImportError:
    import taxonomia


def aplicar(con):
    """Aplica a migration completa: tabelas, população e backfill."""
    if not _criar_tabelas(con):
        return False

    raw_para_materia_id = _popular_materias(con)
    if raw_para_materia_id is None:
        return False

    if not _popular_conteudos(con, raw_para_materia_id):
        return False

    if not _backfill_conteudo_id(con, raw_para_materia_id):
        return False

    return True


def _criar_tabelas(con):
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS materias ("
            "id SERIAL PRIMARY KEY, nome TEXT UNIQUE NOT NULL)"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS conteudos ("
            "id SERIAL PRIMARY KEY,"
            " materia_id INTEGER NOT NULL REFERENCES materias(id),"
            " nome TEXT NOT NULL,"
            " UNIQUE (materia_id, nome))"
        )
        con.execute(
            "ALTER TABLE questoes ADD COLUMN IF NOT EXISTS conteudo_id"
            " INTEGER REFERENCES conteudos(id)"
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_conteudo ON questoes(conteudo_id)")
        con.commit()
        print("✅ Tabelas materias/conteudos e coluna conteudo_id criadas")
        return True
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao criar tabelas materias/conteudos: {e}")
        return False


def _popular_materias(con):
    """Agrupa variantes de `materia` que `taxonomia.normalizar()` trata como
    a mesma coisa, e cria uma linha em `materias` por grupo (nome = a
    variante com mais questões). Devolve {materia_raw: materia_id} para
    todas as variantes vistas, ou None se algo falhou."""
    try:
        linhas = con.execute(
            "SELECT materia, COUNT(*) total FROM questoes"
            " WHERE materia IS NOT NULL AND TRIM(materia) != '' GROUP BY materia"
        ).fetchall()
    except Exception as e:
        print(f"❌ Erro ao ler matérias distintas: {e}")
        return None

    grupos: dict[str, list[tuple[str, int]]] = {}
    for linha in linhas:
        chave = taxonomia.normalizar(linha["materia"])
        grupos.setdefault(chave, []).append((linha["materia"], linha["total"]))

    raw_para_materia_id: dict[str, int] = {}
    try:
        existentes = con.execute("SELECT id, nome FROM materias").fetchall()
        norm_para_id = {taxonomia.normalizar(r["nome"]): (r["id"], r["nome"]) for r in existentes}

        for chave, variantes in grupos.items():
            canonico = max(variantes, key=lambda v: v[1])[0]

            if chave in norm_para_id:
                materia_id, nome_atual = norm_para_id[chave]
                if nome_atual != canonico:
                    con.execute(
                        "UPDATE materias SET nome = %s WHERE id = %s",
                        (canonico, materia_id),
                    )
                    norm_para_id[chave] = (materia_id, canonico)
            else:
                cur = con.execute(
                    "INSERT INTO materias (nome) VALUES (%s)"
                    " ON CONFLICT (nome) DO UPDATE SET nome = EXCLUDED.nome"
                    " RETURNING id",
                    (canonico,),
                )
                materia_id = cur.fetchone()["id"]
                norm_para_id[chave] = (materia_id, canonico)

            for nome_raw, _ in variantes:
                raw_para_materia_id[nome_raw] = materia_id

        con.commit()
        print(
            f"✅ {len(grupos)} matérias populadas"
            f" ({len(raw_para_materia_id)} variantes agrupadas)"
        )
        return raw_para_materia_id
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao popular matérias: {e}")
        return None


def _popular_conteudos(con, raw_para_materia_id):
    try:
        linhas = con.execute(
            "SELECT DISTINCT materia, categoria FROM questoes"
            " WHERE categoria IS NOT NULL AND categoria != ''"
        ).fetchall()
        total = 0
        for linha in linhas:
            materia_id = raw_para_materia_id.get(linha["materia"])
            if materia_id is None:
                continue
            con.execute(
                "INSERT INTO conteudos (materia_id, nome) VALUES (%s, %s)"
                " ON CONFLICT (materia_id, nome) DO NOTHING",
                (materia_id, linha["categoria"]),
            )
            total += 1
        con.commit()
        print(f"✅ Conteúdos populados a partir de categoria ({total} pares matéria/categoria)")
        return True
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao popular conteúdos: {e}")
        return False


def _backfill_conteudo_id(con, raw_para_materia_id):
    try:
        total = 0
        for materia_raw, materia_id in raw_para_materia_id.items():
            cur = con.execute(
                "UPDATE questoes SET conteudo_id = c.id"
                " FROM conteudos c"
                " WHERE questoes.materia = %s"
                "   AND questoes.categoria = c.nome"
                "   AND c.materia_id = %s"
                "   AND questoes.conteudo_id IS NULL",
                (materia_raw, materia_id),
            )
            total += cur.rowcount
        con.commit()
        print(f"✅ Backfill de conteudo_id aplicado ({total} questões)")
        return True
    except Exception as e:
        con.rollback()
        print(f"❌ Erro no backfill de conteudo_id: {e}")
        return False
