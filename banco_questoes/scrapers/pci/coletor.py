"""Orquestração da coleta do PCI Concursos: paginação, checkpoint e persistência.

Diferente de `parser.py` (puro), este módulo faz I/O: chama a rede (via a
sessão HTTP compartilhada de `scrapers.http_utils`) e o banco (via `db`),
usando `fonte='pci'` para checkpoint (`progresso_scraper`) e persistência
(`questoes`).
"""
import sys
from pathlib import Path

# Garante que banco_questoes/ (onde vivem db.py e config.py) esteja no
# sys.path, independentemente de como este módulo é importado/executado.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from . import db  # noqa: E402
except ImportError:
    from banco_questoes import db  # noqa: E402

try:
    from . import config  # noqa: E402
    from . import parser  # noqa: E402
    from .. import http_utils  # noqa: E402
except ImportError:
    from banco_questoes.scrapers.pci import config, parser  # noqa: E402
    from banco_questoes.scrapers import http_utils  # noqa: E402

BASE_URL = "https://www.pciconcursos.com.br/simulados"

# Limite de segurança por tema, para nunca entrar em loop infinito caso a
# heurística de "fim de paginação" falhe por algum motivo.
MAX_PAGINAS_POR_TEMA = 200


def _url_pagina(categoria, tema_nome, pagina):
    if pagina == 1:
        return f"{BASE_URL}/{categoria}/{tema_nome}"
    return f"{BASE_URL}/{categoria}/{tema_nome}/{pagina}"


def coletar_tema(sessao, categoria, tema_nome, tema_url, con):
    """Coleta todas as questões de um tema, com checkpoint após cada página.

    Retoma a partir da última página salva em `progresso_scraper`
    (fonte='pci', chave='{categoria}/{tema_nome}'), então é seguro chamar de
    novo depois de uma interrupção.
    """
    materia = config.get_materia_do_tema(categoria, tema_nome)
    if not materia:
        print(f"  aviso: tema não mapeado, pulando: {categoria}/{tema_nome}")
        return 0

    chave = f"{categoria}/{tema_nome}"
    pagina_inicial = db.obter_progresso(con, "pci", chave) + 1
    total_novas = 0

    for pagina in range(pagina_inicial, MAX_PAGINAS_POR_TEMA + 1):
        url = _url_pagina(categoria, tema_nome, pagina)
        resposta = sessao.get(url, timeout=getattr(sessao, "timeout", 30))

        if resposta.status_code == 404:
            break
        resposta.raise_for_status()

        questoes = parser.extrair_questoes_pagina(resposta.text)
        if not questoes:
            break

        for q in questoes:
            salvou = db.salvar_questao(con, {
                "id_qc": q["id_pci"],
                "enunciado": q["enunciado"],
                "alternativas": q["alternativas"],
                "gabarito": None,
                "comentario": None,
                "materia": materia,
                "assunto": None,
                "banca": q.get("banca"),
                "orgao": q.get("orgao"),
                "ano": q.get("ano"),
                "prova": q.get("prova"),
                "fonte": "pci",
                "texto_associado": q.get("texto_associado"),
                "imagens": q.get("imagens"),
            })
            if salvou:
                total_novas += 1

        db.salvar_progresso(con, "pci", chave, pagina)
        http_utils.aguardar()

    print(f"  {categoria}/{tema_nome}: {total_novas} questões novas")
    return total_novas


def coletar_categoria(sessao, categoria, con):
    """Descobre os temas de uma categoria e coleta cada um deles."""
    resposta = sessao.get(f"{BASE_URL}/{categoria}", timeout=getattr(sessao, "timeout", 30))
    if resposta.status_code == 404:
        print(f"categoria não encontrada: {categoria}")
        return 0
    resposta.raise_for_status()

    temas = parser.descobrir_temas_do_html(resposta.text, categoria)
    if not temas:
        print(f"nenhum tema encontrado para: {categoria}")
        return 0

    print(f"categoria {categoria}: {len(temas)} temas encontrados")
    total_novas = 0
    for tema_nome, tema_url in temas.items():
        total_novas += coletar_tema(sessao, categoria, tema_nome, tema_url, con)
        http_utils.aguardar()

    print(f"categoria {categoria}: {total_novas} questões novas no total")
    return total_novas


def coletar_multiplas_categorias(categorias):
    """Ponto de entrada principal: coleta todas as categorias solicitadas.

    Erros em uma categoria não interrompem as demais (são logados e a coleta
    segue para a próxima categoria da lista).
    """
    sessao = http_utils.criar_sessao()
    con = db.conectar()
    try:
        for categoria in categorias:
            try:
                coletar_categoria(sessao, categoria, con)
            except Exception as e:
                print(f"  {categoria}: erro ({e}), continuando com a próxima")
                continue
    finally:
        con.close()


if __name__ == "__main__":
    coletar_multiplas_categorias(config.listar_categorias())
