"""Abre o Chrome (perfil dedicado do scraper), espera você logar no QC e salva
o HTML da lista de questões.

Uso:
    python salvar_html_exemplo.py                 # salva em pagina_qc_nova.html
    python salvar_html_exemplo.py --fixture       # sobrescreve a fixture dos testes

Seu Chrome normal pode ficar aberto — o scraper usa um perfil separado, e o
login fica guardado nele para as próximas execuções do scraper_qc.py.

Atenção: a lista pública do QC já mostra questões para quem NÃO está logado.
Por isso a espera é pelo sinal de login (some o link /conta/entrar), nunca pela
simples presença de questões na página.
"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

PERFIL = Path(__file__).resolve().parent / "perfil_chrome_scraper"
URL = "https://www.qconcursos.com/questoes-de-concursos/questoes"

DESTINO_PADRAO = Path(__file__).resolve().parent / "tests" / "fixtures" / "pagina_qc_nova.html"
DESTINO_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "pagina_qc.html"

# Marcadores que só existem enquanto ninguém está logado.
_MARCADORES_DESLOGADO = ('href="/conta/entrar"', "q-mobile-signed-out")
_PADRAO_QUESTAO = re.compile(r"Q\d{5,}")


def esta_logado(html: str) -> bool:
    """True quando a página não traz nenhum marcador de sessão anônima."""
    if not html:
        return False
    return not any(marcador in html for marcador in _MARCADORES_DESLOGADO)


def tem_questoes(html: str) -> bool:
    """True quando a página já listou questões (id no formato Q0000000)."""
    return bool(html) and bool(_PADRAO_QUESTAO.search(html))


def aguardar_login(pagina: Page, tentativas: int = 120, intervalo: int = 5) -> bool:
    """Espera o login acontecer na janela aberta. Devolve True se logou.

    Recebe a página já aberta — quem abre e fecha o navegador é o `main`.
    """
    for tentativa in range(tentativas):
        html = pagina.content()
        if esta_logado(html) and tem_questoes(html):
            return True
        if tentativa and tentativa % 12 == 0:
            print(f"  ainda deslogado ({tentativa * intervalo}s)… faça o login na janela do Chrome.")
        time.sleep(intervalo)
    return False


def capturar(pagina: Page, destino: Path) -> Path:
    """Salva o HTML atual da página no destino. Devolve o caminho gravado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(pagina.content(), encoding="utf-8")
    return destino


def main() -> None:
    destino = DESTINO_FIXTURE if "--fixture" in sys.argv else DESTINO_PADRAO
    if destino == DESTINO_FIXTURE:
        print("ATENÇÃO: vai sobrescrever a fixture usada pelos testes.")

    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            str(PERFIL), channel="chrome", headless=False)
        try:
            pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
            pagina.goto(URL, timeout=60000)
            print("Janela aberta. Faça login no QConcursos nela.")
            print("O script detecta o login sozinho e salva (espera até 10 min).")

            if not aguardar_login(pagina):
                print("Login não detectado no tempo limite — nada foi salvo.")
                print("O perfil do Chrome guarda o login: rode de novo depois de entrar.")
                return

            arquivo = capturar(pagina, destino)
            print(f"Logado. Salvo: {arquivo} ({arquivo.stat().st_size} bytes)")
        finally:
            contexto.close()


if __name__ == "__main__":
    main()
