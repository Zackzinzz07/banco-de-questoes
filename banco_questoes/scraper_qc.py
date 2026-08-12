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
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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


def abrir_chrome():
    """Abre o Chrome (via Playwright) usando o perfil dedicado do scraper.

    Login precisa ser feito uma vez interativamente (ver
    salvar_html_exemplo.py); depois disso o perfil mantém a sessão salva em
    disco e as próximas aberturas já entram logadas.

    Retorna o BrowserContext (persistente); a página inicial é
    `contexto.pages[0]` (ou `contexto.new_page()` se ainda não houver
    nenhuma). É responsabilidade de quem chama fechar o contexto
    (`contexto.close()`) ao terminar.
    """
    p = sync_playwright().start()
    return p.chromium.launch_persistent_context(
        str(PERFIL_CHROME), channel="chrome", headless=False)
