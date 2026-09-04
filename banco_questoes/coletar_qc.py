"""Orquestrador da coleta no QConcursos.

Uso:
    python coletar_qc.py              # coleta enunciados
    python coletar_qc.py gabaritos    # responde as pendentes, respeitando a cota

Camada de orquestração (CLAUDE.md 1.2): coordena as três outras camadas sem
fazer o trabalho delas — navegação vem de `scraper_qc`, leitura de HTML de
`scrapers/qc/parser`, gravação de `db`. Navegador e conexão são abertos e
fechados aqui, em `try/finally`.
"""

import sys

from playwright.sync_api import sync_playwright

import scraper_qc
from scrapers.qc import disciplinas, parser

try:
    from . import db
except ImportError:
    import db


def salvar_pagina(html: str, con, materia: str) -> int:
    """Salva as questões de uma página no banco; retorna quantas eram novas."""
    novas = 0
    for q in parser.extrair_blocos(html):
        salvou = db.salvar_questao(
            con,
            {
                "id_qc": q["id_qc"],
                "enunciado": q["enunciado"],
                "alternativas": q["alternativas"],
                "gabarito": None,
                "materia": materia,
                "assunto": q["assunto"],
                "categoria": q["categoria"],
                "tema": q["tema"],
                "cargo": q["cargo"],
                "banca": q["banca"],
                # O órgão é o da prova de origem da questão, extraído da própria
                # página. Sobrescrever por um valor fixo faria questão de outro
                # estado se passar por questão do concurso alvo.
                "orgao": q["orgao"],
                "ano": q["ano"],
                "prova": q["prova"],
                "fonte": "qconcursos",
                "texto_associado": q["texto_associado"],
                "imagens": q["imagens"],
            },
        )
        if salvou:
            novas += 1
        else:
            db.completar_texto_associado(con, q["id_qc"], q["texto_associado"], q["imagens"])
    return novas


def aguardar_acao_humana(aba, motivo: str, tentativas: int = 18, intervalo: int = 10) -> bool:
    """Não falha rápido: avisa o que a tela pede e espera o humano resolver na
    janela do Chrome já aberta. Recarrega a cada `intervalo` segundos por até
    tentativas*intervalo segundos (3 min por padrão)."""
    import time

    print(f"  Ação humana necessária: {motivo}")
    print(f"  Resolva na janela do Chrome (aguardando até {tentativas * intervalo // 60} min)…")
    url_atual = aba.url
    for tentativa in range(tentativas):
        time.sleep(intervalo)
        aba.goto(url_atual, timeout=60000)
        if not parser.bloqueio_pagina(aba.content()):
            print("  Liberado — continuando.")
            return True
        print(f"  ainda bloqueado ({(tentativa + 1) * intervalo}s)…")
    return False


def _responder_questao(aba, bloco, numero: str) -> str | None:
    """Marca uma alternativa e clica em responder. Devolve a letra marcada."""
    seletor_radio = f'{parser.SELETORES["alternativa_radio"]}[name="answer-question-{numero}"]'
    radio = bloco.select_one(seletor_radio)
    letra_marcada = (radio.get("value") or "").strip().upper() if radio else None
    if not letra_marcada:
        print(f"  Q{numero}: sem alternativa para marcar — pulando.")
        return None
    try:
        aba.locator(seletor_radio).first.click(timeout=5000)
        aba.locator(f'{parser.SELETORES["botao_responder"]}[data-question-id="{numero}"]').click(
            timeout=5000
        )
    except Exception:
        print(f"  Q{numero}: não consegui clicar em responder — pulando.")
        return None
    return letra_marcada


def _pendentes_por_materia(con) -> dict:
    por_materia: dict = {}
    for q in db.sem_gabarito(con):
        if q["id_qc"]:
            por_materia.setdefault(q["materia"], set()).add(q["id_qc"][1:])
    return por_materia


def materias_a_coletar(con=None) -> list[tuple[str, str]]:
    """Devolve (matéria, url de busca) de tudo que há para coletar no QC.

    A fonte é `scrapers/qc/disciplinas.py`, não o `edital.py`: o edital
    descreve UM concurso (o SEDES/DF), e enquanto ele mandava na coleta os
    outros 8 concursos configurados não coletavam questão nenhuma.

    Com a conexão, ordena da menos coletada para a mais coletada. São 23
    disciplinas e a cota é de 40 páginas por matéria, então a ordem decide o
    que entra antes de a sessão acabar: Língua Portuguesa chegou à página 149
    rendendo zero por página enquanto Noções de Informática, com 70 mil
    questões no QC, seguia intocada.
    """
    itens = [(nome, disciplinas.url_de_busca(ids)) for nome, ids in disciplinas.listar()]
    if con is None:
        return itens
    return sorted(itens, key=lambda item: db.obter_progresso(con, "qconcursos", item[0]))


def coletar_gabaritos(limite_questoes: int | None = None) -> None:
    """Responde as questões pendentes direto na página de listagem, respeitando
    a cota diária gratuita do QC.

    `limite_questoes`: só para validação manual — encerra depois de N gabaritos
    nesta chamada, sem esperar a cota real do site.
    """
    con = db.conectar()
    por_materia = _pendentes_por_materia(con)
    if not por_materia:
        print("Nenhuma questão pendente de gabarito.")
        con.close()
        return
    total = sum(len(v) for v in por_materia.values())
    print(f"{total} questões sem gabarito; usando a cota diária…")

    coletadas = 0
    parar = False
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p)
        try:
            for materia, url_base in materias_a_coletar(con):
                if parar:
                    break
                faltam = por_materia.get(materia)
                if not faltam:
                    continue
                pagina = 1
                while faltam and not parar and pagina <= scraper_qc.MAX_PAGINAS_POR_MATERIA:
                    aba.goto(scraper_qc.url_pagina(url_base, pagina), timeout=60000)
                    scraper_qc.pausa()
                    html = aba.content()
                    bloqueio = parser.bloqueio_pagina(html)
                    if bloqueio:
                        if not aguardar_acao_humana(aba, bloqueio):
                            print("  Não resolvido a tempo — encerrando os gabaritos por hoje.")
                            break
                        html = aba.content()
                    blocos = parser.mapa_blocos(html)
                    if not blocos:
                        break  # acabaram as páginas dessa matéria
                    for numero in [n for n in blocos if n in faltam]:
                        if limite_questoes is not None and coletadas >= limite_questoes:
                            print(f"Limite de validação ({limite_questoes}) atingido.")
                            parar = True
                            break
                        if parser.botao_bloqueado(blocos[numero]):
                            print(
                                "  Botão de responder desabilitado — a permissão da conta pode"
                                " ter regredido. Confira o QConcursos e rode de novo."
                            )
                            parar = True
                            break
                        letra = _responder_questao(aba, blocos[numero], numero)
                        faltam.discard(numero)
                        if not letra:
                            continue
                        scraper_qc.pausa()
                        html_pos = aba.content()
                        if parser.atingiu_limite(html_pos):
                            print(
                                f"Limite diário do QC atingido. Coletados {coletadas} gabaritos"
                                " hoje; rode de novo amanhã."
                            )
                            parar = True
                            break
                        bloco_pos = parser.mapa_blocos(html_pos).get(numero)
                        gabarito, comentario = parser.extrair_resposta_do_bloco(
                            str(bloco_pos) if bloco_pos is not None else html_pos, letra
                        )
                        if gabarito:
                            db.atualizar_gabarito(con, f"Q{numero}", gabarito, comentario)
                            coletadas += 1
                            print(f"  Q{numero}: {gabarito}")
                        else:
                            print(f"  Q{numero}: resposta não localizada — pulando.")
                    pagina += 1
        finally:
            contexto.close()
            con.close()
    print(f"Fase de gabaritos encerrada: {coletadas} coletados.")


# Página sem bloco nenhum não prova que o conteúdo acabou: o QConcursos
# devolve erro 500 intermitente (confirmado ao vivo — discipline_ids[]=213 deu
# 500 numa sessão e voltou ao normal na seguinte). Antes, uma única página
# assim encerrava a matéria: Direito Administrativo parou na página 20 com
# 80.542 questões disponíveis. Só desiste depois de N vazias em sequência.
VAZIAS_SEGUIDAS_PARA_DESISTIR = 3


def coletar_materia(aba, con, materia: str, url_base: str) -> int:
    """Percorre as páginas de uma matéria e grava o que achar.

    Recebe a aba do Playwright e a conexão já abertas (CLAUDE.md 2); quem as
    abre e fecha é o orquestrador. Devolve o total de questões novas.
    """
    pagina = db.obter_progresso(con, "qconcursos", materia) + 1
    fim = pagina + scraper_qc.MAX_PAGINAS_POR_MATERIA
    total_novas = 0
    vazias_seguidas = 0

    while pagina < fim:
        aba.goto(scraper_qc.url_pagina(url_base, pagina))
        scraper_qc.pausa()
        html = aba.content()
        total_blocos = len(parser.extrair_blocos(html))

        if total_blocos == 0:
            vazias_seguidas += 1
            limite = VAZIAS_SEGUIDAS_PARA_DESISTIR
            print(f"[{materia}] página {pagina}: vazia ({vazias_seguidas}/{limite})")
            if vazias_seguidas >= VAZIAS_SEGUIDAS_PARA_DESISTIR:
                print(
                    f"[{materia}] {vazias_seguidas} páginas vazias seguidas — encerrando a matéria."
                )
                break
            pagina += 1
            continue

        vazias_seguidas = 0
        novas = salvar_pagina(html, con, materia)
        total_novas += novas
        print(f"[{materia}] página {pagina}: {novas} novas ({total_blocos} na página)")
        # Só grava progresso em página que rendeu: assim uma falha transitória
        # não faz a próxima rodada pular o trecho que ficou por coletar.
        db.salvar_progresso(con, "qconcursos", materia, pagina)
        pagina += 1

    return total_novas


def coletar_enunciados() -> None:
    con = db.conectar()
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p)
        try:
            for materia, url_base in materias_a_coletar(con):
                coletar_materia(aba, con, materia, url_base)
        finally:
            contexto.close()
            con.close()


def main() -> None:
    fase = sys.argv[1] if len(sys.argv) > 1 else "enunciados"
    try:
        if fase == "gabaritos":
            coletar_gabaritos()
        else:
            coletar_enunciados()
    except KeyboardInterrupt:
        print("\nInterrompido — progresso salvo. Rode de novo para retomar.")
    except Exception as erro:
        print(f"Erro inesperado ({erro.__class__.__name__}: {erro}).")
        print("Confira internet/login no QC e rode de novo.")
        sys.exit(1)


if __name__ == "__main__":
    main()
