"""Abre o Chrome (perfil dedicado do scraper), espera você logar no QC
e salva o HTML da lista de questões como fixture. Seu Chrome normal pode
ficar aberto — o scraper usa um perfil separado."""
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

PERFIL = Path(__file__).resolve().parent / "perfil_chrome_scraper"
URL = "https://www.qconcursos.com/questoes-de-concursos/questoes"

with sync_playwright() as p:
    contexto = p.chromium.launch_persistent_context(
        str(PERFIL), channel="chrome", headless=False)
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    pagina.goto(URL)
    print("Janela aberta. Faça login no QConcursos nela (se ainda não estiver).")
    print("O script salva sozinho quando as questões aparecerem (até 10 min).")
    html = ""
    for _ in range(120):
        html = pagina.content()
        if re.search(r"Q\d{5,}", html):
            break
        time.sleep(5)
    destino = Path(__file__).parent / "tests" / "fixtures" / "pagina_qc.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"Salvo: {destino} ({destino.stat().st_size} bytes)")
    contexto.close()
