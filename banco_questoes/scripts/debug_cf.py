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
            url = "https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]=1"
            aba.goto(url, timeout=60000)
            time.sleep(2)
            title = aba.title()
            html = aba.content()
            
            print("Title:", title)
            print("Contains 'just a moment':", "just a moment" in title.lower())
            print("Contains 'um momento' in title:", "um momento" in title.lower())
            
            # Procurar onde 'cloudflare' aparece no html
            soup = BeautifulSoup(html, "html.parser")
            matches = [str(tag) for tag in soup.find_all(True) if "cloudflare" in str(tag).lower()]
            print(f"Total de tags contendo 'cloudflare': {len(matches)}")
            for m in matches[:3]:
                print("  Match snippet:", m[:150])
                
        finally:
            contexto.close()

if __name__ == "__main__":
    main()
