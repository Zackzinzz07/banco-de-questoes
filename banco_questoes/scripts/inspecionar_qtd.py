import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper_qc

def main():
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p, headless=False)
        try:
            url = "https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]=46"
            aba.goto(url, timeout=60000)
            aba.wait_for_timeout(3000)
            
            html = aba.content()
            soup = BeautifulSoup(html, "html.parser")
            
            # Procurar qualquer texto contendo 'questõ' ou números grandes
            print("--- Procurando por textos de contagem no HTML ---")
            for tag in soup.find_all(["span", "div", "h2", "h3", "p", "strong", "small"]):
                text = tag.get_text(strip=True)
                if "questõ" in text.lower() or "questoes" in text.lower() or "encontrada" in text.lower() or "resultado" in text.lower():
                    if len(text) < 150:
                        print(f"[{tag.name}.{tag.get('class')}] -> {text}")

        finally:
            contexto.close()

if __name__ == "__main__":
    main()
