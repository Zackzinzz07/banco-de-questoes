"""Scraper do QConcursos usando um perfil Chrome dedicado do scraper (Selenium + BS4).

Se o site mudar de layout, ajuste apenas o dicionário SELETORES abaixo.

O perfil padrão do sistema operacional NÃO é usado: Chrome recentes recusam
depuração remota (o mecanismo que o Selenium usa para controlar o navegador)
quando --user-data-dir aponta para o diretório de perfil padrão do SO
("DevTools remote debugging requires a non-default data directory"). Por
isso usamos um perfil dedicado só para o scraper (PERFIL_CHROME abaixo,
dentro do próprio projeto), populado via login interativo em
salvar_html_exemplo.py e nunca commitado (ver .gitignore).
"""
import re
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
    """Abre o Chrome usando o perfil dedicado do scraper (PERFIL_CHROME).

    Login precisa ser feito uma vez interativamente (ver
    salvar_html_exemplo.py); depois disso o perfil mantém a sessão salva em
    disco e as próximas aberturas já entram logadas.
    """
    opcoes = Options()
    opcoes.add_argument(f"--user-data-dir={PERFIL_CHROME}")
    return webdriver.Chrome(options=opcoes)
