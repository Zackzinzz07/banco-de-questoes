"""Importa questões do SQLite legado (pré-PostgreSQL) para o banco atual.

Uso:
    python -m scripts.importar_sqlite [caminho_do_sqlite]

O SQLite antigo não tem as colunas `cargo`, `categoria` e `tema` — elas ficam
nulas, coerente com a regra de nunca inventar metadado que a fonte não trouxe.
O dedupe por `content_hash` do `db.salvar_questao` torna a importação
idempotente: rodar de novo não duplica nada.
"""
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

try:
    import db
except ImportError:  # rodando de fora da pasta do projeto
    from banco_questoes import db

PADRAO_SQLITE = Path(__file__).resolve().parent.parent / "banco_de_questoes.db"

_CAMPOS = ("id_qc", "enunciado", "alternativas", "gabarito", "comentario",
           "materia", "assunto", "banca", "orgao", "ano", "prova", "fonte",
           "texto_associado", "imagens")


def _json_ou_padrao(texto: str | None, padrao: Any) -> Any:
    """Decodifica JSON do SQLite; devolve `padrao` se vier vazio ou corrompido."""
    if not texto:
        return padrao
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return padrao


def ler_questoes(caminho: Path | str) -> list[dict[str, Any]]:
    """Lê o SQLite legado e devolve dicts no formato aceito por `db.salvar_questao`.

    Descarta linhas sem enunciado ou sem alternativas — o banco novo exige
    ambos (NOT NULL / dedupe por conteúdo) e uma questão assim é inútil num
    simulado.
    """
    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        linhas = con.execute(
            f"SELECT {', '.join(_CAMPOS)} FROM questoes").fetchall()
    finally:
        con.close()

    questoes: list[dict[str, Any]] = []
    for linha in linhas:
        enunciado = (linha["enunciado"] or "").strip()
        alternativas = _json_ou_padrao(linha["alternativas"], {})
        if not enunciado or not alternativas:
            continue
        questoes.append({
            "id_qc": linha["id_qc"],
            "enunciado": enunciado,
            "alternativas": alternativas,
            "gabarito": linha["gabarito"],
            "comentario": linha["comentario"],
            "materia": linha["materia"],
            "assunto": linha["assunto"],
            "banca": linha["banca"],
            "orgao": linha["orgao"],
            "ano": linha["ano"],
            "prova": linha["prova"],
            "fonte": linha["fonte"],
            "texto_associado": linha["texto_associado"],
            "imagens": _json_ou_padrao(linha["imagens"], []),
        })
    return questoes


def importar(questoes: list[dict[str, Any]], con) -> tuple[int, int]:
    """Grava as questões no banco atual. Devolve (importadas, duplicadas).

    Recebe a conexão já aberta — quem abre e fecha é o orquestrador (`main`).
    """
    importadas = duplicadas = 0
    for questao in questoes:
        if db.salvar_questao(con, questao):
            importadas += 1
        else:
            duplicadas += 1
    return importadas, duplicadas


def main() -> None:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO_SQLITE
    if not caminho.exists():
        print(f"SQLite não encontrado: {caminho}")
        sys.exit(1)

    questoes = ler_questoes(caminho)
    print(f"{len(questoes)} questões lidas de {caminho.name}")

    con = db.conectar()
    try:
        importadas, duplicadas = importar(questoes, con)
    finally:
        con.close()

    print(f"importadas: {importadas} | já existiam: {duplicadas}")


if __name__ == "__main__":
    main()
