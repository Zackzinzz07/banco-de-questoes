"""Camada de automação do Instituto AOCP (CLAUDE.md 1.2): apenas Playwright.

O site é uma SPA renderizada no cliente: uma requisição HTTP pura (requests)
não devolve links de concurso nem PDFs -- por isso, ao contrário da Cebraspe
e do IADES, aqui todo o fluxo depende de um navegador real. A prova e o
gabarito, em especial, só existem depois de escolher cargo/tipo na
ferramenta "Visualizar Cadernos de Questões e Gabarito Definitivo": o PDF
sai de uma URL assinada da S3 (expira em minutos) e o gabarito é uma grade
HTML renderizada na hora, não um arquivo.

O AOCP fica atrás do Cloudflare, que bloqueia o Chromium headless padrão
("Just a moment..."). Mesma situação do QConcursos (scraper_qc.py) -- a
solução aqui é a mesma: Chrome real (`channel="chrome"`), perfil persistente
e janela visível (`headless=False`).
"""

from pathlib import Path

from playwright.sync_api import Page

BASE_URL = "https://www.institutoaocp.org.br"
PAGINAS_LISTAGEM = ("concursos/status/inscricoes-abertas", "concursos/status/finalizados")
PERFIL_CHROME = Path(__file__).resolve().parent.parent.parent / "perfil_chrome_scraper"

TIMEOUT_MS = 30000
_TITULOS_DESAFIO = ("um momento", "just a moment")


def _esperar_cloudflare(page: Page, tentativas: int = 3) -> None:
    """Dá tempo do desafio de segurança do Cloudflare se resolver sozinho.

    Um navegador real passa automaticamente em alguns segundos; só
    re-navegamos se a página de desafio ainda estiver lá depois da espera.
    """
    for tentativa in range(tentativas):
        if page.title().strip().lower() not in _TITULOS_DESAFIO:
            return
        page.wait_for_timeout(5000)
        if page.title().strip().lower() not in _TITULOS_DESAFIO:
            return
        if tentativa < tentativas - 1:
            page.reload(timeout=TIMEOUT_MS)


def abrir_navegador(p, headless: bool = False):
    """Chrome real com o perfil dedicado do scraper (mesmo perfil de scraper_qc.py).

    Recebe a instância do sync_playwright (use `with sync_playwright() as p:`);
    quem abre e fecha o contexto é o orquestrador (coletar_aocp.py).
    """
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL_CHROME), channel="chrome", headless=headless
    )
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    return contexto, pagina


def abrir_listagem(page: Page, pagina_status: str) -> str:
    """Abre uma página de listagem de concursos por status e devolve o HTML renderizado."""
    page.goto(f"{BASE_URL}/{pagina_status}", timeout=TIMEOUT_MS)
    _esperar_cloudflare(page)
    page.wait_for_selector('a[href^="/concursos/"]', timeout=TIMEOUT_MS)
    return page.content()


def abrir_concurso(page: Page, concurso_id: str) -> str:
    """Abre a página de um concurso e devolve o HTML (publicações e link da prova)."""
    page.goto(f"{BASE_URL}/concursos/{concurso_id}", timeout=TIMEOUT_MS)
    _esperar_cloudflare(page)
    # O layout usa abas (headlessui) em telas estreitas: o conteúdo pode estar
    # no DOM mas oculto. "attached" basta -- só precisamos do HTML, não de
    # interagir com esses elementos.
    page.wait_for_selector(
        'a[href*="arquivos-site.institutoaocp"], a[href*="open-link?identificador"]',
        timeout=TIMEOUT_MS,
        state="attached",
    )
    return page.content()


def abrir_visualizador_prova(page: Page, link_visualizar: str) -> str:
    """Abre/reabre a ferramenta de prova e gabarito, com o formulário limpo."""
    page.goto(link_visualizar, timeout=TIMEOUT_MS)
    _esperar_cloudflare(page)
    page.wait_for_selector("#cargo", timeout=TIMEOUT_MS)
    return page.content()


def capturar_prova(
    page: Page, cargo: str, tipo: str, timeout_ms: int = 15000
) -> dict[str, str] | None:
    """Seleciona cargo/tipo, clica "Ver prova" e captura a URL do PDF + o HTML do gabarito.

    Devolve None quando a combinação cargo/tipo não existe para este
    concurso: o site AOCP não bloqueia a seleção de combinações inválidas,
    apenas não carrega o iframe da prova.
    """
    page.locator("#cargo").select_option(label=cargo)
    page.locator("#tipo_prova").select_option(label=tipo)
    page.get_by_role("button", name="Ver prova").click()
    try:
        page.wait_for_selector("iframe", timeout=timeout_ms)
    except Exception:
        return None
    pdf_url = page.locator("iframe").get_attribute("src")
    if not pdf_url:
        return None
    return {"pdf_url": pdf_url, "html": page.content()}


def baixar_pdf(page: Page, url: str) -> bytes:
    """Baixa os bytes de um PDF usando o contexto de rede do navegador."""
    resposta = page.context.request.get(url)
    if not resposta.ok:
        raise RuntimeError(f"Download falhou ({resposta.status}): {url[:80]}")
    return resposta.body()
