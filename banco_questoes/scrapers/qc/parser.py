"""Parsing do HTML do QConcursos: recebe string, devolve dados. 100% puro.

Sem rede e sem banco — quem navega é `scraper_qc.py`, quem grava é o
orquestrador. Se o QC mudar de layout, ajuste apenas SELETORES.
"""

import re

from bs4 import BeautifulSoup

# ── SELETORES CENTRALIZADOS ────────────────────────────────────────────────
# Calibrados contra fixture real (tests/fixtures/pagina_qc.html). Divergências
# do palpite original:
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
    "info": ".q-question-info",  # linha com Ano/Banca/Órgão/Prova(s)
    "breadcrumb": ".q-question-breadcrumb",  # matéria e assunto (links <a>)
    # Texto-base/imagem da questão. Vem no HTML mesmo com o bloco recolhido
    # (Bootstrap collapse esconde só por CSS) — não precisa clicar.
    "texto_associado": "div[id$='-text'].collapse",
    # Fase de gabaritos — calibrados contra o markup REAL capturado ao vivo na
    # própria página de LISTAGEM. Achado importante: cada bloco de questão já
    # carrega sua própria UI de resposta (rádios + "Responder" + feedback); não
    # precisa navegar para a página individual da questão — aliás essa URL usa
    # um slug opaco (ex.: "/questoes/7080448c-94") que não dá pra reconstruir a
    # partir do id_qc, então nem daria certo.
    "botao_responder": "button.js-answer-btn",
    "alternativa_radio": "input.js-question-answer",
    # Só é preenchido (texto ou aria-label) quando a alternativa marcada estava
    # ERRADA — fica no trecho "Incorreta. Gabarito oficial da banca: <span ...>".
    # Quando a marcada é a certa, esse span fica vazio e o gabarito é a própria
    # letra marcada (ver extrair_resposta_do_bloco).
    "resposta_certa": ".js-question-right-answer",
    "feedback_correto": ".js-response-correct",  # "Parabéns! Você acertou!"
    "feedback_errado": ".js-response-wrong",
    # data-limit-reached="true" no próprio botão de responder é o sinal
    # primário da cota diária esgotada; o id abaixo é o modal que a UI abre
    # nesse caso (o QC tem mais de um componente de aviso de limite; cobrimos
    # ambos os sinais em atingiu_limite).
    "modal_limite": "#js-questions-limit-modal, "
    "[data-limit-feedback='resolveQuestionLimit'][data-limit-reached='true']",
    "modal_nao_confirmado": "#js-account-not-confirm-modal",
}

# Campos da linha de metadados (".q-question-info"). No HTML real os campos não
# são separados por "|"/"•" (só as múltiplas provas dentro de "Provas:" são);
# por isso cada campo é capturado até o próximo rótulo conhecido ou o fim.
_CAMPO_INFO = re.compile(
    r"(Ano|Banca|[ÓO]rg[ãa]o|Provas?):\s*(.*?)\s*(?=(?:Ano|Banca|[ÓO]rg[ãa]o|Provas?):|$)"
)


def _texto(no) -> str:
    return " ".join(no.get_text(" ").split()) if no else ""


def campos_info(texto: str) -> dict:
    """Extrai {Ano, Banca, Órgão, Prova} da linha de metadados como dict."""
    campos = {}
    for rotulo, valor in _CAMPO_INFO.findall(texto):
        chave = "Prova" if rotulo.startswith("Prova") else rotulo
        valor = valor.rstrip(" |")  # "Provas:" pode ter várias provas unidas por "|"
        if valor:
            campos[chave] = valor
    return campos


def extrair_cargo_da_prova(
    prova: str | None, banca: str | None, ano: str | None, orgao: str | None
) -> str | None:
    """Isola o cargo do texto de uma prova ("Banca - Ano - Órgão - Cargo").

    Usa banca/ano/órgão já extraídos como prefixo em vez de fazer split por
    " - ", porque o nome do órgão pode ter hífen (ex.: "Câmara de Jardim - MS").
    Só considera a 1ª prova quando há mais de uma (campo "Provas:" com "|").
    """
    if not prova or not banca or not ano or not orgao:
        return None
    primeira_prova = prova.split("|")[0].strip()
    prefixo = f"{banca} - {ano} - {orgao}"
    if not primeira_prova.startswith(prefixo):
        return None
    resto = primeira_prova[len(prefixo) :].strip(" -")
    return resto or None


def _trilha(bloco) -> list[str]:
    """Breadcrumb como lista: matéria + 1 a 3 níveis de conteúdo."""
    return [_texto(a).rstrip(" ,") for a in bloco.select(f"{SELETORES['breadcrumb']} a")]


def _alternativas(bloco) -> dict:
    alternativas = {}
    for i, alt in enumerate(bloco.select(SELETORES["alternativa"])):
        letra_no = alt.select_one(SELETORES["letra_alternativa"])
        letra = _texto(letra_no)[:1].upper() if letra_no else "ABCDE"[i]
        texto_alt = _texto(alt)
        if letra_no:
            texto_alt = texto_alt.replace(_texto(letra_no), "", 1).strip()
        alternativas[letra] = texto_alt
    return alternativas


def _questao_do_bloco(bloco) -> dict:
    id_match = re.search(r"Q\d+", _texto(bloco.select_one(SELETORES["id"])))
    campos = campos_info(_texto(bloco.select_one(SELETORES["info"])))
    ano = re.search(r"\d{4}", campos.get("Ano", ""))
    # A trilha tem tamanho variável e o schema só tem categoria e tema, então um
    # eventual 4º nível (o mais granular) é descartado.
    trilha = _trilha(bloco)
    area = bloco.select_one(SELETORES["texto_associado"])
    return {
        "id_qc": id_match.group(0) if id_match else None,
        "enunciado": _texto(bloco.select_one(SELETORES["enunciado"])),
        "alternativas": _alternativas(bloco),
        "materia_qc": trilha[0] if trilha else None,
        "assunto": trilha[1] if len(trilha) > 1 else None,
        "categoria": trilha[1] if len(trilha) > 1 else None,
        "tema": trilha[2] if len(trilha) > 2 else None,
        "ano": int(ano.group(0)) if ano else None,
        "banca": campos.get("Banca") or None,
        "orgao": campos.get("Órgão") or None,
        "cargo": extrair_cargo_da_prova(
            campos.get("Prova"), campos.get("Banca"), campos.get("Ano"), campos.get("Órgão")
        ),
        "prova": campos.get("Prova") or None,
        "texto_associado": _texto(area) if area else "",
        "imagens": [i.get("src") for i in area.select("img") if i.get("src")] if area else [],
    }


def extrair_blocos(html: str) -> list[dict]:
    """Extrai todas as questões de uma página de busca do QC."""
    sopa = BeautifulSoup(html, "html.parser")
    questoes = [_questao_do_bloco(b) for b in sopa.select(SELETORES["bloco"])]
    return [q for q in questoes if q["id_qc"] and q["enunciado"] and q["alternativas"]]


def atingiu_limite(html: str) -> bool:
    """True quando a cota diária de questões grátis foi esgotada.

    Dois sinais (achado de calibração ao vivo): o botão "Responder" carrega
    `data-limit-reached="true"`; e/ou a UI abre um modal cujo texto menciona
    "limite diário". Não vasculhamos a página inteira pelo texto — o aviso pode
    estar sempre no HTML, escondido por CSS, o que daria falso positivo sempre.
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


def extrair_resposta_do_bloco(bloco_html: str, letra_marcada: str | None):
    """Depois de responder marcando `letra_marcada`, devolve (gabarito, comentário).

    Regras (calibração ao vivo): SELETORES["resposta_certa"] só vem preenchido
    quando a marcada estava ERRADA — aí a letra ali é o gabarito oficial. Senão,
    se houver feedback de acerto, o gabarito é a própria letra marcada. Senão,
    não dá pra saber.

    O comentário do professor só carrega via AJAX ao abrir a aba "Comentários",
    que esta fase não clica — devolvemos None em vez de inventar.
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


def bloqueio_pagina(html: str) -> str | None:
    """Mensagem PT-BR se a página exigir ação humana (ex.: conta não confirmada)."""
    sopa = BeautifulSoup(html, "html.parser")
    if sopa.select_one(SELETORES["modal_nao_confirmado"]):
        return "Conta não confirmada no QConcursos — confirme o e-mail e rode de novo."
    return None


def mapa_blocos(html: str) -> dict:
    """numero_id (sem o "Q") -> bloco da questão, só os que têm botão de responder."""
    sopa = BeautifulSoup(html, "html.parser")
    mapa = {}
    for bloco in sopa.select(SELETORES["bloco"]):
        botao = bloco.select_one(SELETORES["botao_responder"])
        numero = botao.get("data-question-id") if botao else None
        if numero:
            mapa[numero] = bloco
    return mapa


def botao_bloqueado(bloco) -> bool:
    """True se o botão de responder está desabilitado — permissão da conta regrediu."""
    botao = bloco.select_one(SELETORES["botao_responder"])
    if not botao:
        return True
    return botao.get("aria-disabled") == "true" or botao.has_attr("disabled")
