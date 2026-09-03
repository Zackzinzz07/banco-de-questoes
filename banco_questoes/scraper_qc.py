"""Automação do navegador para o QConcursos: abrir, navegar, pausar.

Camada de automação (CLAUDE.md 1.2): só Playwright. Não interpreta HTML — isso
é de `scrapers/qc/parser.py` — e não grava nada — isso é de `coletar_qc.py`.

O perfil padrão do sistema operacional NÃO é usado: Chrome recentes recusam
depuração remota (o mecanismo que ferramentas de automação usam para controlar
o navegador) quando apontado para o diretório de perfil padrão do SO
("DevTools remote debugging requires a non-default data directory"). Por isso
usamos um perfil dedicado só para o scraper (PERFIL_CHROME abaixo, dentro do
próprio projeto), populado via login interativo em salvar_html_exemplo.py e
nunca commitado (ver .gitignore).
"""

import random
import time
from pathlib import Path

PERFIL_CHROME = Path(__file__).resolve().parent / "perfil_chrome_scraper"

# O Cloudflare do QC bloqueia navegador invisível ("Um momento…"); a coleta roda
# com janela visível — pode minimizar que ela trabalha sozinha.
HEADLESS = False

PAUSA_MIN, PAUSA_MAX = 3, 6
MAX_PAGINAS_POR_MATERIA = 40  # limite por sessão diária, por educação


def abrir_navegador(p, headless: bool = HEADLESS):
    """Chrome com o perfil dedicado do scraper (login fica salvo nele).

    Recebe a instância do sync_playwright (use `with sync_playwright() as p:`);
    quem abre e fecha o contexto é o orquestrador.
    """
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL_CHROME), channel="chrome", headless=headless
    )
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    return contexto, pagina


def url_pagina(url_base: str, pagina: int) -> str:
    separador = "&" if "?" in url_base else "?"
    return f"{url_base}{separador}page={pagina}"


def pausa() -> None:
    """Intervalo aleatório entre requisições, para não martelar o site."""
    time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))
