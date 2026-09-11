"""Orquestrador AOCP (CLAUDE.md 1.2): abre o Playwright uma vez e coordena
automação (scrapers/aocp/automacao.py) + parsing (scrapers/aocp/parser.py)
+ persistência (JSON em disco).

Diferente da Cebraspe, aqui não existe PDF de caderno linkado direto na
página do concurso: prova e gabarito só aparecem depois de escolher
cargo/tipo na ferramenta "Visualizar Cadernos de Questões e Gabarito
Definitivo". O PDF baixado fica só em memória (nunca é gravado em disco),
então não há nada bruto para purgar depois -- mais enxuto que o ciclo
Process & Purge da Cebraspe/base_scraper.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scrapers.aocp import automacao, parser

PASTA = Path(__file__).resolve().parent / "provas_pdf" / "aocp"


def coletar_concurso(page, concurso_id: str, pasta_base: Path) -> int:
    """Coleta edital + todas as combinações cargo/tipo de um concurso.

    Devolve quantos itens (questão + alternativas + gabarito) extraiu.
    """
    html_concurso = automacao.abrir_concurso(page, concurso_id)
    publicacoes = parser.extrair_publicacoes_html(html_concurso)
    edital = parser.extrair_edital_abertura(publicacoes)
    link_prova = parser.extrair_link_visualizar_prova(html_concurso)

    destino = pasta_base / concurso_id
    destino.mkdir(parents=True, exist_ok=True)

    if edital:
        (destino / "edital.json").write_text(
            json.dumps(edital, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    if not link_prova:
        print("  [SEM PROVA] concurso ainda não publicou cadernos/gabarito")
        return 0

    html_visualizador = automacao.abrir_visualizador_prova(page, link_prova)
    cargos, tipos = parser.extrair_opcoes_prova(html_visualizador)

    todos_itens: list[dict] = []
    gabarito_geral: dict[str, dict[int, str]] = {}
    for cargo in cargos:
        for tipo in tipos:
            automacao.abrir_visualizador_prova(page, link_prova)
            resultado = automacao.capturar_prova(page, cargo, tipo)
            if resultado is None:
                continue
            gabarito = parser.extrair_gabarito_html(resultado["html"])
            if not gabarito:
                continue
            gabarito_geral[f"{cargo} | {tipo}"] = gabarito
            try:
                pdf_bytes = automacao.baixar_pdf(page, resultado["pdf_url"])
            except Exception as erro:
                print(f"  [SKIP] {cargo} / {tipo}: {erro.__class__.__name__}")
                continue
            itens = parser.extrair_itens(pdf_bytes, gabarito)
            for item in itens:
                item["cargo"] = cargo
                item["tipo_prova"] = tipo
                item["concurso"] = concurso_id
                item["banca"] = "Instituto AOCP"
            todos_itens.extend(itens)

    if gabarito_geral:
        (destino / "gabarito.json").write_text(
            json.dumps(gabarito_geral, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    if todos_itens:
        (destino / "itens.json").write_text(
            json.dumps(todos_itens, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return len(todos_itens)


def coletar_todos(concurso_ids: list[str] | None = None) -> None:
    with sync_playwright() as p:
        contexto, page = automacao.abrir_navegador(p)
        try:
            if concurso_ids is None:
                concurso_ids = []
                for pagina in automacao.PAGINAS_LISTAGEM:
                    html = automacao.abrir_listagem(page, pagina)
                    concurso_ids.extend(c["id"] for c in parser.extrair_concursos_html(html))
                concurso_ids = sorted(set(concurso_ids), key=int, reverse=True)

            print(f"AOCP — {len(concurso_ids)} concursos a varrer")
            total = 0
            for indice, concurso_id in enumerate(concurso_ids, 1):
                print(f"[{indice}/{len(concurso_ids)}] concurso {concurso_id}")
                try:
                    extraidos = coletar_concurso(page, concurso_id, PASTA)
                except Exception as erro:
                    print(f"  ERRO {erro.__class__.__name__}: {erro}")
                    continue
                total += extraidos
                print(f"  {extraidos} itens")
            print(f"Total: {total} itens extraídos")
        finally:
            contexto.close()


def main() -> None:
    coletar_todos(sys.argv[1:] or None)


if __name__ == "__main__":
    main()
