"""Migra questões do banco SQLite legado (banco_de_questoes.db) para o
PostgreSQL, corrigindo a fonte de questões do PCI que foram gravadas
incorretamente como 'quadrix_pdf' no protótipo original.

Regra de remapeamento: fonte == 'quadrix_pdf' AND id_qc IS NOT NULL -> 'pci'
(essas linhas na verdade vieram do scraper do PCI; todas as demais linhas
permanecem com a fonte original).

Uso (a partir de banco_questoes/):
    python scripts/migrar_sqlite_para_postgres.py

Reaproveita db.salvar_questao(), que já faz dedupe (por hash do enunciado
e por id_qc) e commit/rollback por linha -- então o script é seguro de
rodar mais de uma vez.
"""
import json
import sqlite3
import sys
from pathlib import Path

# Garante que banco_questoes/ (onde vivem db.py e config.py) esteja no
# sys.path, independentemente de o script ser rodado diretamente
# (python scripts/migrar_sqlite_para_postgres.py) ou importado como
# scripts.migrar_sqlite_para_postgres com banco_questoes/ já no path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402  (mantido pelo import check / uso futuro de settings)
import db  # noqa: E402

SQLITE_PATH = Path(__file__).resolve().parent.parent / "banco_de_questoes.db"


def remapear_fonte(fonte, id_qc):
    """Questões gravadas como 'quadrix_pdf' com id_qc preenchido eram, na
    verdade, coletadas pelo scraper do PCI (bug do protótipo original);
    aqui a fonte é corrigida para 'pci'. Todas as outras linhas (incluindo
    'quadrix_pdf' sem id_qc, e 'qconcursos') não são alteradas."""
    if fonte == "quadrix_pdf" and id_qc is not None:
        return "pci"
    return fonte


def linha_para_questao(row):
    """Converte uma sqlite3.Row da tabela questoes no dict esperado por
    db.salvar_questao(). Pode lançar json.JSONDecodeError/TypeError se os
    campos JSON (alternativas/imagens) estiverem corrompidos -- quem chama
    decide o que fazer (a migração deve pular a linha, não abortar)."""
    colunas = row.keys()
    alternativas = json.loads(row["alternativas"])
    imagens_raw = row["imagens"] if "imagens" in colunas else None
    imagens = json.loads(imagens_raw) if imagens_raw else None
    return {
        "id_qc": row["id_qc"],
        "enunciado": row["enunciado"],
        "alternativas": alternativas,
        "gabarito": row["gabarito"],
        "comentario": row["comentario"] if "comentario" in colunas else None,
        "materia": row["materia"],
        "assunto": row["assunto"],
        "banca": row["banca"],
        "orgao": row["orgao"],
        "ano": row["ano"],
        "prova": row["prova"],
        "fonte": remapear_fonte(row["fonte"], row["id_qc"]),
        "texto_associado": row["texto_associado"] if "texto_associado" in colunas else None,
        "imagens": imagens,
    }


def migrar(sqlite_con, postgres_con):
    """Itera as questões do SQLite, remapeia a fonte e insere no Postgres
    via db.salvar_questao (que já faz dedupe). Nunca aborta a migração
    inteira por causa de uma linha ruim -- registra o erro e continua.
    Retorna (inseridas, duplicadas, erros)."""
    inseridas = 0
    duplicadas = 0
    erros = 0

    linhas = sqlite_con.execute("SELECT * FROM questoes").fetchall()
    for row in linhas:
        id_qc = row["id_qc"] if "id_qc" in row.keys() else None

        try:
            q = linha_para_questao(row)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            erros += 1
            print(f"[erro] id_qc={id_qc!r}: falha ao parsear JSON da linha ({e}); pulando.")
            continue

        try:
            inserida = db.salvar_questao(postgres_con, q)
        except Exception as e:  # nunca deixa uma linha ruim derrubar a migração
            erros += 1
            print(f"[erro] id_qc={id_qc!r}: falha ao salvar no Postgres ({e}); pulando.")
            try:
                postgres_con.rollback()  # limpa a transação abortada e permite continuar
            except Exception:
                pass
            continue

        if inserida:
            inseridas += 1
        else:
            duplicadas += 1

    return inseridas, duplicadas, erros


def imprimir_resumo_por_fonte(postgres_con):
    linhas = postgres_con.execute(
        "SELECT fonte, COUNT(*) AS total FROM questoes GROUP BY fonte ORDER BY fonte"
    ).fetchall()
    print("\nDistribuição por fonte no Postgres (após a migração):")
    for linha in linhas:
        print(f"  {linha['fonte']}: {linha['total']}")


def main():
    if not SQLITE_PATH.exists():
        print(f"Arquivo SQLite não encontrado ({SQLITE_PATH}). Nada a migrar.")
        return 0

    sqlite_con = sqlite3.connect(SQLITE_PATH)
    sqlite_con.row_factory = sqlite3.Row

    try:
        postgres_con = db.conectar()
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL ({config.DATABASE_URL}): {e}")
        sqlite_con.close()
        return 1

    try:
        inseridas, duplicadas, erros = migrar(sqlite_con, postgres_con)
        print(
            f"\nTotal: {inseridas} inseridas, {duplicadas} duplicadas (já existiam), "
            f"{erros} com erro."
        )
        imprimir_resumo_por_fonte(postgres_con)
    finally:
        sqlite_con.close()
        postgres_con.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
