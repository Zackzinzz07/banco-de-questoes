import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper_qc

def main():
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p, headless=False)
        try:
            for id_test in [0, 9999, 5000]:
                url = f"https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]={id_test}"
                aba.goto(url, timeout=60000)
                time.sleep(2)
                title = aba.title()
                soup = BeautifulSoup(aba.content(), "html.parser")
                h2 = soup.select_one("h2.q-page-results-title")
                h2_text = h2.get_text(strip=True) if h2 else "NENHUM H2"
                print(f"ID {id_test}: Title='{title}' | H2='{h2_text}'")
        finally:
            contexto.close()

if __name__ == "__main__":
    main()
