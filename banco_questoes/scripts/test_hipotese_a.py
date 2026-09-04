import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Garante import do scraper_qc
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper_qc

IDS_TESTE = [
    (46, "Noções de Informática"),
    (4, "Raciocínio Lógico"),
    (9, "Direito Penal"),
]

def extrair_info_pagina(html: str, title: str):
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Título
    print(f"  Title: {title}")
    
    # 2. Tentar extrair do título ou h1/h2/filtros
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else None
    print(f"  H1: {h1_text}")
    
    # 3. Procurar por contador de questões
    # Padrões comuns: ".q-total-results", ".q-counter", "span.q-text-bold", text regex
    # Vamos buscar no DOM elementos relevantes
    count_text = None
    for selector in [".q-total-results", ".q-counter", ".q-pagination-total", "span.q-text-bold", ".q-heading-title"]:
        el = soup.select_one(selector)
        if el:
            print(f"  Selector {selector}: {el.get_text(strip=True)}")
            
    # Procurar por tags de filtro ativas
    filtros = soup.select(".q-filter-tag, .q-chip, .badge, .q-breadcrumb")
    for f in filtros:
        print(f"  Filtro tag: {f.get_text(strip=True)}")

def main():
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p, headless=False)
        try:
            for id_disc, nome_esperado in IDS_TESTE:
                url = f"https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]={id_disc}"
                print(f"\n--- Testando ID {id_disc} (Esperado: {nome_esperado}) ---")
                print(f"Navegando para: {url}")
                aba.goto(url, timeout=60000)
                time.sleep(3)
                
                title = aba.title()
                html = aba.content()
                
                # Verificar se apareceu Cloudflare ou login
                if "Just a moment" in title or "Um momento" in html or "Cloudflare" in html:
                    print("⚠️ Cloudflare ativado!")
                    break
                    
                extrair_info_pagina(html, title)
                
        finally:
            contexto.close()

if __name__ == "__main__":
    main()
