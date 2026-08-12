"""Abre o Chrome com um perfil dedicado do scraper, espera o usuário logar
manualmente no QConcursos e salva o HTML da página de busca como fixture.

Na primeira vez, o perfil (banco_questoes/perfil_chrome_scraper/) está vazio
e sem login: o script abre a janela, o usuário loga (pode usar Google) e o
script detecta sozinho quando a lista de questões carregou.
"""
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PERFIL = Path(__file__).resolve().parent / "perfil_chrome_scraper"
URL = "https://www.qconcursos.com/questoes-de-concursos/questoes"
INTERVALO_SEGUNDOS = 5
TIMEOUT_SEGUNDOS = 10 * 60
RE_ID_QUESTAO = re.compile(r"Q\d{5,}")

opcoes = Options()
opcoes.add_argument(f"--user-data-dir={PERFIL}")
driver = webdriver.Chrome(options=opcoes)
driver.get(URL)

print(
    "Uma janela do Chrome abriu. Faça login no QConcursos nela (pode usar "
    "Google). O script continua sozinho quando as questões aparecerem."
)

destino = Path(__file__).parent / "tests" / "fixtures" / "pagina_qc.html"
destino.parent.mkdir(parents=True, exist_ok=True)

inicio = time.time()
encontrado = False
while time.time() - inicio < TIMEOUT_SEGUNDOS:
    html = driver.page_source
    if RE_ID_QUESTAO.search(html):
        encontrado = True
        break
    time.sleep(INTERVALO_SEGUNDOS)

if encontrado:
    destino.write_text(html, encoding="utf-8")
    print(f"Salvo: {destino} ({destino.stat().st_size} bytes)")
else:
    print(
        f"Tempo esgotado ({TIMEOUT_SEGUNDOS // 60} min) sem detectar "
        "questões na página (nenhum código Qxxxxx encontrado). Nada foi "
        "salvo. Verifique se o login foi concluído e tente novamente."
    )

driver.quit()
