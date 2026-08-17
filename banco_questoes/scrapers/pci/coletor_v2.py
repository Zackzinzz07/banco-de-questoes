"""Coletor PCI v2: Coleta com hierarquia completa (categoria/subcategoria/tema)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from banco_questoes import db
except ImportError:
    import db

try:
    from . import config, parser
    from .. import http_utils
except ImportError:
    from banco_questoes.scrapers.pci import config, parser
    from banco_questoes.scrapers import http_utils

BASE_URL = "https://www.pciconcursos.com.br/simulados"
MAX_PAGINAS_POR_TEMA = 200


def _url_pagina(categoria, tema_slug, pagina):
    """Monta URL com ou sem número de página.

    PCI estrutura: /simulados/categoria/tema ou /simulados/categoria/tema/pagina
    """
    if pagina == 1:
        return f"{BASE_URL}/{categoria}/{tema_slug}"
    return f"{BASE_URL}/{categoria}/{tema_slug}/{pagina}"


def coletar_tema_v2(sessao, categoria, tema_slug, tema_nome, tema_url, con):
    """Coleta todas as questões de um tema com hierarquia completa.

    Nota: PCI tem estrutura /simulados/categoria/tema (sem subcategoria)
    """
    materia = config.get_materia_do_tema(categoria, tema_slug)
    if not materia:
        # Fallback: sem mapeamento específico = pula
        print(f"    [WARN] tema não mapeado: {categoria}/{tema_slug}")
        return 0

    chave = f"{categoria}/{tema_slug}"
    pagina_inicial = db.obter_progresso(con, "pci", chave) + 1
    total_novas = 0

    print(f"    [PAGE] {categoria}/{tema_slug}: coletando a partir da página {pagina_inicial}...")

    for pagina in range(pagina_inicial, MAX_PAGINAS_POR_TEMA + 1):
        url = _url_pagina(categoria, tema_slug, pagina)
        resposta = sessao.get(url, timeout=getattr(sessao, "timeout", 30))

        if resposta.status_code == 404:
            break
        resposta.raise_for_status()

        questoes = parser.extrair_questoes_pagina(resposta.text)
        if not questoes:
            break

        for q in questoes:
            salvou = db.salvar_questao(con, {
                "id_qc": q.get("id_pci"),
                "enunciado": q.get("enunciado"),
                "alternativas": str(q.get("alternativas", "")),
                "gabarito": None,
                "comentario": None,
                "materia": materia,
                "assunto": None,
                "banca": q.get("banca"),
                "orgao": q.get("orgao") or "PCI",
                "ano": q.get("ano"),
                "prova": q.get("prova"),
                "fonte": "pci",
                "texto_associado": q.get("texto_associado"),
                "imagens": q.get("imagens", []),
                "imagens_urls": q.get("imagens_urls", []),
                # NEW: Hierarquia (categoria/tema apenas)
                "categoria": categoria,
                "tema": tema_slug,
            }, cargo=None)
            if salvou:
                total_novas += 1

        db.salvar_progresso(con, "pci", chave, pagina)
        http_utils.aguardar()

        if total_novas % 50 == 0:
            print(f"      [OK] {total_novas} questoes coletadas até agora...")

    print(f"      [DONE] {total_novas} questoes novas em {chave}")
    return total_novas


def coletar_categoria_v2(sessao, categoria, con):
    """Coleta todos os temas (chamados subcategorias no UI) de uma categoria."""
    resposta = sessao.get(f"{BASE_URL}/{categoria}", timeout=getattr(sessao, "timeout", 30))
    if resposta.status_code == 404:
        print(f"categoria não encontrada: {categoria}")
        return 0
    resposta.raise_for_status()

    # Descobrir temas (UI chama de subcategorias)
    subcategorias = parser.descobrir_subcategorias_do_html(resposta.text, categoria)
    if not subcategorias:
        print(f"nenhum tema encontrado para: {categoria}")
        return 0

    print(f"\n[CATEGORY] {categoria}: {len(subcategorias)} temas descobertos")

    total_novas = 0
    for tema_slug, tema_data in subcategorias.items():
        print(f"  [TEMA] {tema_slug}...")
        total_novas += coletar_tema_v2(
            sessao,
            categoria,
            tema_slug,
            tema_data["nome"],
            tema_data["url"],
            con
        )
        http_utils.aguardar()

    print(f"\n[SUCCESS] {categoria}: {total_novas} questoes novas no total\n")
    return total_novas


def coletar_multiplas_categorias_v2(categorias):
    """Coleta todas as categorias com nova hierarquia."""
    sessao = http_utils.criar_sessao()
    con = db.conectar()

    print("\n" + "="*80)
    print("COLETA PCI v2 - HIERARQUIA COMPLETA (categoria/tema)")
    print("="*80)

    try:
        for categoria in categorias:
            try:
                coletar_categoria_v2(sessao, categoria, con)
            except Exception as e:
                print(f"[ERROR] {categoria}: erro ({e})")
                continue
    finally:
        con.close()

    print("\n" + "="*80)
    print("[COMPLETE] Coleta finalizada!")
    print("="*80)


if __name__ == "__main__":
    coletar_multiplas_categorias_v2(config.listar_categorias())
