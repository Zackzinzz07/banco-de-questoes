"""Panorama do banco de questões: quanto já foi coletado, por matéria e fonte.

Uso:
    .venv/bin/python -m scripts.status              # panorama geral
    .venv/bin/python -m scripts.status --materia    # detalhe por matéria
    .venv/bin/python -m scripts.status --vivo       # atualiza a cada 15s

Leitura apenas — não escreve nada no banco.
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402

SQL_POR_FONTE = """
SELECT fonte,
       COUNT(*)          AS total,
       COUNT(gabarito)   AS gabarito,
       COUNT(cargo)      AS cargo,
       COUNT(banca)      AS banca,
       COUNT(categoria)  AS categoria
  FROM questoes
 GROUP BY fonte
 ORDER BY total DESC
"""

SQL_POR_MATERIA = """
SELECT COALESCE(materia, '(sem matéria)') AS materia,
       fonte,
       COUNT(*)        AS total,
       COUNT(gabarito) AS gabarito,
       COUNT(cargo)    AS cargo
  FROM questoes
 GROUP BY materia, fonte
 ORDER BY total DESC
"""


def _barra(parte: int, total: int, largura: int = 18) -> str:
    """Barra de proporção em texto — quanto de `total` está preenchido."""
    if total <= 0:
        return " " * largura
    cheio = round(largura * parte / total)
    return "█" * cheio + "·" * (largura - cheio)


def _pct(parte: int, total: int) -> str:
    return f"{(100 * parte / total):5.1f}%" if total else "    —"


def imprimir_por_fonte(con: db._Conexao) -> int:
    """Resumo por fonte. Devolve o total de questões no banco."""
    linhas = con.execute(SQL_POR_FONTE).fetchall()
    total_geral = sum(linha["total"] for linha in linhas)

    print(f"{'FONTE':<14}{'QUESTÕES':>10}   {'GABARITO':>16}   {'CARGO':>16}")
    print("─" * 64)
    for linha in linhas:
        n = linha["total"]
        print(
            f"{linha['fonte']:<14}{n:>10}   "
            f"{_barra(linha['gabarito'], n, 8)} {_pct(linha['gabarito'], n)}   "
            f"{_barra(linha['cargo'], n, 8)} {_pct(linha['cargo'], n)}"
        )
    print("─" * 64)
    print(f"{'TOTAL':<14}{total_geral:>10}")
    return total_geral


def imprimir_por_materia(con: db._Conexao, limite: int = 40) -> None:
    """Detalhe por matéria — o que cada fonte trouxe de cada assunto."""
    linhas = con.execute(SQL_POR_MATERIA).fetchall()
    print()
    print(f"{'MATÉRIA':<36}{'FONTE':<13}{'QTD':>7}{'GABARITO':>11}{'CARGO':>9}")
    print("─" * 76)
    for linha in linhas[:limite]:
        print(
            f"{linha['materia'][:35]:<36}{linha['fonte']:<13}{linha['total']:>7}"
            f"{linha['gabarito']:>11}{linha['cargo']:>9}"
        )
    if len(linhas) > limite:
        print(f"... e mais {len(linhas) - limite} combinações matéria/fonte")


def imprimir_progresso_scrapers(con: db._Conexao) -> None:
    """Última página processada por scraper — de onde uma nova rodada retoma."""
    linhas = con.execute(
        "SELECT fonte, chave, ultima_pagina FROM progresso_scraper"
        " ORDER BY ultima_pagina DESC LIMIT 10"
    ).fetchall()
    if not linhas:
        return
    total = con.execute("SELECT COUNT(*) AS n FROM progresso_scraper").fetchone()["n"]
    print()
    print(f"PROGRESSO DOS SCRAPERS — {total} chaves, top 10 por profundidade")
    print("─" * 68)
    for linha in linhas:
        print(f"  {linha['fonte']:<12} {linha['chave'][:42]:<44} pág. {linha['ultima_pagina']}")


def rodar(detalhar: bool, vivo: bool) -> None:
    anterior = None
    while True:
        con = db.conectar()
        try:
            if vivo:
                os.system("clear")
                print(time.strftime("%H:%M:%S"))
            total = imprimir_por_fonte(con)
            if anterior is not None:
                delta = total - anterior
                print(
                    f"{'':14}{'+' + str(delta) if delta else 'sem novas':>10} desde a última leitura"
                )
            anterior = total
            if detalhar:
                imprimir_por_materia(con)
                imprimir_progresso_scrapers(con)
        finally:
            con.close()

        if not vivo:
            return
        time.sleep(15)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materia", action="store_true", help="detalha por matéria")
    parser.add_argument("--vivo", action="store_true", help="atualiza a cada 15s")
    args = parser.parse_args()
    try:
        rodar(detalhar=args.materia, vivo=args.vivo)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
