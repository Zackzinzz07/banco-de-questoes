"""Scraper do QConcursos usando um perfil Chrome dedicado do scraper (Playwright + BS4).

Se o site mudar de layout, ajuste apenas o dicionário SELETORES abaixo.

O perfil padrão do sistema operacional NÃO é usado: Chrome recentes recusam
depuração remota (o mecanismo que ferramentas de automação usam para
controlar o navegador) quando apontado para o diretório de perfil padrão do
SO ("DevTools remote debugging requires a non-default data directory"). Por
isso usamos um perfil dedicado só para o scraper (PERFIL_CHROME abaixo,
dentro do próprio projeto), populado via login interativo em
salvar_html_exemplo.py e nunca commitado (ver .gitignore).
"""
import random
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import db
import edital

# ── SELETORES CENTRALIZADOS (ajustar aqui se o QC mudar o layout) ──────────
# Calibrados contra fixture real (tests/fixtures/pagina_qc.html): ver notas
# de calibração no task-7-report.md. Divergências do palpite original:
#   - alternativas: cada uma é um <label class="q-radio-button ..."> (não
#     havia ".q-item-choice" no HTML real).
#   - letra_alternativa: a letra fica em ".q-option-item"; ".q-item-enum" é
#     na verdade o TEXTO da alternativa, não a letra.
SELETORES = {
    "bloco": "div.q-question-item",
    "id": ".q-id",
    "enunciado": ".q-question-enunciation",
    "alternativa": "label.q-radio-button",
    "letra_alternativa": ".q-option-item",
    "info": ".q-question-info",           # linha com Ano/Banca/Órgão/Prova(s)
    "breadcrumb": ".q-question-breadcrumb",  # matéria e assunto (links <a>)
    # Fase de gabaritos — calibrados contra o markup REAL capturado ao vivo na
    # própria página de LISTAGEM (busca por matéria). Achado importante: cada
    # bloco de questão já carrega sua própria UI de resposta (rádios +
    # "Responder" + feedback); não precisa navegar para a página individual da
    # questão — aliás essa URL usa um slug opaco (ex.: "/questoes/7080448c-94")
    # que não dá pra reconstruir a partir do id_qc, então nem daria certo.
    "botao_responder": "button.js-answer-btn",
    "alternativa_radio": "input.js-question-answer",
    # Só é preenchido (texto ou aria-label) quando a alternativa marcada
    # estava ERRADA — fica dentro de ".js-response-wrong", no trecho
    # "Incorreta. Gabarito oficial da banca: <span ...>". Quando a alternativa
    # marcada é a certa, esse span permanece vazio e o gabarito é a própria
    # letra marcada (ver extrair_resposta_do_bloco e feedback_correto abaixo).
    "resposta_certa": ".js-question-right-answer",
    "feedback_correto": ".js-response-correct",  # "Parabéns! Você acertou!"
    "feedback_errado": ".js-response-wrong",
    # data-limit-reached="true" no próprio botão de responder é o sinal
    # primário da cota diária esgotada; o id abaixo é o modal que a UI abre
    # nesse caso (distinto do antigo "js-question-belt-block-modal" visto em
    # calibração anterior — o QC parece ter mais de um componente de aviso de
    # limite; cobrimos ambos os sinais em atingiu_limite).
    "modal_limite": "#js-questions-limit-modal, "
                     "[data-limit-feedback='resolveQuestionLimit'][data-limit-reached='true']",
    "modal_nao_confirmado": "#js-account-not-confirm-modal",
}

PERFIL_CHROME = Path(__file__).resolve().parent / "perfil_chrome_scraper"

# Campos da linha de metadados (".q-question-info"). No HTML real os campos
# não são separados por "|"/"•" (só as múltiplas provas dentro de "Provas:"
# são); por isso cada campo é capturado até o próximo rótulo conhecido ou o
# fim da string, em vez de até um separador fixo.
_CAMPO_INFO = re.compile(
    r"(Ano|Banca|[ÓO]rg[ãa]o|Provas?):\s*(.*?)\s*(?=(?:Ano|Banca|[ÓO]rg[ãa]o|Provas?):|$)"
)


def _texto(no):
    return " ".join(no.get_text(" ").split()) if no else ""


def _campos_info(texto):
    """Extrai {Ano, Banca, Órgão, Prova} da linha de metadados como dict."""
    campos = {}
    for rotulo, valor in _CAMPO_INFO.findall(texto):
        chave = "Prova" if rotulo.startswith("Prova") else rotulo
        valor = valor.rstrip(" |")  # "Provas:" pode ter várias provas unidas por "|"
        if valor:
            campos[chave] = valor
    return campos


def extrair_blocos(html):
    """Extrai todas as questões de uma página de busca do QC."""
    sopa = BeautifulSoup(html, "html.parser")
    questoes = []
    for bloco in sopa.select(SELETORES["bloco"]):
        id_qc = _texto(bloco.select_one(SELETORES["id"]))
        id_match = re.search(r"Q\d+", id_qc)
        alternativas = {}
        for i, alt in enumerate(bloco.select(SELETORES["alternativa"])):
            letra_no = alt.select_one(SELETORES["letra_alternativa"])
            letra = _texto(letra_no)[:1].upper() if letra_no else "ABCDE"[i]
            texto_alt = _texto(alt)
            if letra_no:
                texto_alt = texto_alt.replace(_texto(letra_no), "", 1).strip()
            alternativas[letra] = texto_alt
        campos = _campos_info(_texto(bloco.select_one(SELETORES["info"])))
        ano = re.search(r"\d{4}", campos.get("Ano", ""))
        links_trilha = bloco.select(f"{SELETORES['breadcrumb']} a")
        materia_qc = _texto(links_trilha[0]) if links_trilha else None
        assunto = _texto(links_trilha[1]).rstrip(" ,") if len(links_trilha) > 1 else None
        questoes.append({
            "id_qc": id_match.group(0) if id_match else None,
            "enunciado": _texto(bloco.select_one(SELETORES["enunciado"])),
            "alternativas": alternativas,
            "materia_qc": materia_qc,
            "assunto": assunto or None,
            "ano": int(ano.group(0)) if ano else None,
            "banca": campos.get("Banca") or None,
            "orgao": campos.get("Órgão") or None,
            "prova": campos.get("Prova") or None,
        })
    return [q for q in questoes if q["id_qc"] and q["enunciado"] and q["alternativas"]]


HEADLESS = False  # o Cloudflare do QC bloqueia navegador invisível ("Um momento…");
                  # a coleta roda com janela visível — pode minimizar que ela trabalha sozinha

PAUSA_MIN, PAUSA_MAX = 3, 6
MAX_PAGINAS_POR_MATERIA = 40  # limite por sessão diária, por educação


def abrir_navegador(p, headless=HEADLESS):
    """Chrome com o perfil dedicado do scraper (login fica salvo nele).

    Recebe a instância do sync_playwright (use `with sync_playwright() as p:`)."""
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL_CHROME), channel="chrome", headless=headless)
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    return contexto, pagina


def url_pagina(url_base, pagina):
    separador = "&" if "?" in url_base else "?"
    return f"{url_base}{separador}page={pagina}"


def salvar_pagina(html, con, materia):
    """Salva as questões de uma página no banco; retorna quantas eram novas."""
    novas = 0
    for q in extrair_blocos(html):
        salvou = db.salvar_questao(con, {
            "id_qc": q["id_qc"],
            "enunciado": q["enunciado"],
            "alternativas": q["alternativas"],
            "gabarito": None,
            "materia": materia,
            "assunto": q["assunto"],
            "banca": q["banca"],
            "orgao": q["orgao"],
            "ano": q["ano"],
            "prova": q["prova"],
            "fonte": "qconcursos",
        })
        novas += 1 if salvou else 0
    return novas


def _pausa():
    time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))


def atingiu_limite(html):
    """True quando a cota diária de questões grátis foi esgotada.

    Dois sinais, combinados (achado de calibração ao vivo): o próprio botão
    "Responder" carrega `data-limit-reached="true"` quando a cota acabou; e/ou
    a UI abre um modal de limite (ver SELETORES["modal_limite"]) cujo texto
    menciona "limite diário". Não vasculhamos o texto da página inteira por
    "limite diário" (lição de uma calibração anterior com outro modal do QC:
    o texto do aviso pode estar sempre presente no HTML, escondido por CSS,
    então isso daria falso positivo em toda página) — só o texto de dentro do
    modal quando ele de fato casa com o seletor.
    """
    sopa = BeautifulSoup(html, "html.parser")
    for botao in sopa.select(SELETORES["botao_responder"]):
        if botao.get("data-limit-reached") == "true":
            return True
    modal = sopa.select_one(SELETORES["modal_limite"])
    if modal:
        texto = _texto(modal).lower()
        if "limite diário" in texto or "limite diario" in texto:
            return True
    return False


def extrair_resposta_do_bloco(bloco_html, letra_marcada):
    """Depois de responder uma questão (marcando `letra_marcada`): retorna
    (letra_do_gabarito, comentario_ou_None).

    Regras (achado de calibração ao vivo, ver notas em SELETORES):
      - SELETORES["resposta_certa"] só vem preenchido (texto ou aria-label)
        quando a alternativa marcada estava ERRADA — nesse caso a letra ali
        dentro É o gabarito oficial da banca.
      - Senão, se o feedback de acerto (SELETORES["feedback_correto"], "Você
        acertou!") estiver presente, o gabarito é a própria `letra_marcada`.
      - Senão, não dá pra saber (None, None).

    Comentário do professor: o QC só carrega isso via AJAX ao clicar na aba
    "Comentários"/"Gabarito Comentado" da questão — essa fase não clica
    nessa aba, então devolvemos sempre None em vez de inventar um valor.
    """
    sopa = BeautifulSoup(bloco_html, "html.parser")
    resposta_no = sopa.select_one(SELETORES["resposta_certa"])
    if resposta_no:
        letra = (_texto(resposta_no) or resposta_no.get("aria-label") or "").strip().upper()[:1]
        if letra in ("A", "B", "C", "D", "E"):
            return letra, None
    if letra_marcada and sopa.select_one(SELETORES["feedback_correto"]):
        return letra_marcada.upper(), None
    return None, None


def _bloqueio_pagina(html):
    """Se a página exigir ação humana ou sinalizar regressão de permissão da
    conta (ex.: perdeu a confirmação de e-mail), devolve uma mensagem PT-BR;
    senão, None."""
    sopa = BeautifulSoup(html, "html.parser")
    if sopa.select_one(SELETORES["modal_nao_confirmado"]):
        return "Conta não confirmada no QConcursos — confirme o e-mail e rode de novo."
    return None


def _aguardar_acao_humana(aba, motivo, tentativas=18, intervalo=10):
    """Não falha rápido: avisa o que a tela está pedindo e espera o humano
    resolver usando a janela visível do Chrome que já está aberta. Recarrega
    a página atual a cada `intervalo` segundos por até tentativas*intervalo
    segundos (3 min por padrão). Devolve True se a tela liberou, False se
    continuou bloqueada."""
    print(f"  Ação humana necessária: {motivo}")
    print(f"  Resolva na janela do Chrome (aguardando até {tentativas * intervalo // 60} min)…")
    url_atual = aba.url
    for tentativa in range(tentativas):
        time.sleep(intervalo)
        aba.goto(url_atual, timeout=60000)
        if not _bloqueio_pagina(aba.content()):
            print("  Liberado — continuando.")
            return True
        print(f"  ainda bloqueado ({(tentativa + 1) * intervalo}s)…")
    return False


def _mapa_blocos(html):
    """Mapeia numero_id (sem o prefixo "Q") -> Tag do bloco da questão, para
    a página de listagem atual — só inclui blocos que de fato têm o botão de
    responder (ou seja, blocos "respondíveis")."""
    sopa = BeautifulSoup(html, "html.parser")
    mapa = {}
    for bloco in sopa.select(SELETORES["bloco"]):
        botao = bloco.select_one(SELETORES["botao_responder"])
        numero = botao.get("data-question-id") if botao else None
        if numero:
            mapa[numero] = bloco
    return mapa


def _botao_bloqueado(bloco):
    """True se o botão de responder do bloco estiver desabilitado — sinal de
    que a permissão da conta (ex.: confirmação de e-mail) regrediu."""
    botao = bloco.select_one(SELETORES["botao_responder"])
    if not botao:
        return True
    return botao.get("aria-disabled") == "true" or botao.has_attr("disabled")


def coletar_gabaritos(limite_questoes=None):
    """Responde as questões pendentes de gabarito diretamente na página de
    listagem (cada bloco de questão já traz sua própria UI de resposta — ver
    notas de calibração em SELETORES), respeitando a cota diária gratuita do
    QC.

    `limite_questoes`: só para validação manual — encerra depois de coletar
    N gabaritos nesta chamada, sem esperar a cota diária real do site.
    """
    con = db.conectar()
    pendentes = db.sem_gabarito(con)
    if not pendentes:
        print("Nenhuma questão pendente de gabarito.")
        con.close()
        return
    por_materia = {}
    for q in pendentes:
        if not q["id_qc"]:
            continue
        por_materia.setdefault(q["materia"], set()).add(q["id_qc"][1:])
    print(f"{sum(len(v) for v in por_materia.values())} questões sem gabarito; usando a cota diária…")

    coletadas = 0
    limite_atingido = False
    with sync_playwright() as p:
        contexto, aba = abrir_navegador(p)
        try:
            for materia in edital.nomes_materias():
                if limite_atingido:
                    break
                faltam = por_materia.get(materia)
                if not faltam:
                    continue
                url_base = edital.MATERIAS.get(materia, {}).get("url_qc")
                if not url_base:
                    continue
                pagina = 1
                while faltam and not limite_atingido and pagina <= MAX_PAGINAS_POR_MATERIA:
                    aba.goto(url_pagina(url_base, pagina), timeout=60000)
                    _pausa()
                    html = aba.content()
                    bloqueio = _bloqueio_pagina(html)
                    if bloqueio:
                        if not _aguardar_acao_humana(aba, bloqueio):
                            print("  Não foi resolvido a tempo — encerrando a fase de gabaritos por hoje.")
                            limite_atingido = True
                            break
                        html = aba.content()
                    blocos = _mapa_blocos(html)
                    if not blocos:
                        break  # acabaram as páginas dessa matéria
                    for numero in [n for n in blocos if n in faltam]:
                        if limite_atingido:
                            break
                        if limite_questoes is not None and coletadas >= limite_questoes:
                            print(f"Limite de validação ({limite_questoes}) atingido — encerrando.")
                            limite_atingido = True
                            break
                        bloco = blocos[numero]
                        if _botao_bloqueado(bloco):
                            print("  Botão de responder desabilitado — permissão da conta pode"
                                  " ter regredido. Confira o QConcursos e rode de novo.")
                            limite_atingido = True
                            break
                        seletor_radio = f'{SELETORES["alternativa_radio"]}[name="answer-question-{numero}"]'
                        radio = bloco.select_one(seletor_radio)
                        letra_marcada = (radio.get("value") or "").strip().upper() if radio else None
                        if not letra_marcada:
                            print(f"  Q{numero}: sem alternativa para marcar — pulando.")
                            faltam.discard(numero)
                            continue
                        try:
                            aba.locator(seletor_radio).first.click(timeout=5000)
                            aba.locator(
                                f'{SELETORES["botao_responder"]}[data-question-id="{numero}"]'
                            ).click(timeout=5000)
                        except Exception:
                            print(f"  Q{numero}: não consegui clicar em responder — pulando.")
                            faltam.discard(numero)
                            continue
                        _pausa()
                        html_pos = aba.content()
                        faltam.discard(numero)
                        if atingiu_limite(html_pos):
                            print(f"Limite diário do QC atingido. Coletados {coletadas} gabaritos"
                                  " hoje; rode de novo amanhã.")
                            limite_atingido = True
                            break
                        bloco_pos = _mapa_blocos(html_pos).get(numero)
                        gabarito, comentario = extrair_resposta_do_bloco(
                            str(bloco_pos) if bloco_pos is not None else html_pos, letra_marcada)
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


def coletar_enunciados():
    con = db.conectar()
    with sync_playwright() as p:
        contexto, aba = abrir_navegador(p)
        try:
            for materia in edital.nomes_materias():
                url_base = edital.MATERIAS[materia]["url_qc"]
                if not url_base:
                    print(f"[{materia}] sem url_qc no edital.py — pulando.")
                    continue
                pagina = db.obter_progresso(con, materia) + 1
                fim = pagina + MAX_PAGINAS_POR_MATERIA
                while pagina < fim:
                    aba.goto(url_pagina(url_base, pagina))
                    _pausa()
                    html = aba.content()
                    novas = salvar_pagina(html, con, materia)
                    total_blocos = len(extrair_blocos(html))
                    print(f"[{materia}] página {pagina}: {novas} novas ({total_blocos} na página)")
                    db.salvar_progresso(con, materia, pagina)
                    if total_blocos == 0:  # acabaram as páginas (ou caiu o login)
                        break
                    pagina += 1
        finally:
            contexto.close()
            con.close()


if __name__ == "__main__":
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
