import sys
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scraper_qc

KNOWN_IDS = [1, 2, 3, 4, 9, 10, 20, 21, 26, 33, 46, 61, 93, 98, 188, 203, 204, 213, 233, 235, 409, 503, 534]

def parse_page(title: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    
    # Se título for a busca padrão sem filtro
    if "Provas, Aulas e Questões" in title and "sobre" not in title.lower():
        return None, 0, "Inválido / Sem disciplina"
        
    # Tentar extrair nome do título
    # Ex: "Questões de Concurso sobre Noções de Informática | Qconcursos.com"
    # Ex: "Questões de Concurso de Noções de Informática | Qconcursos.com"
    match_nome = re.search(r"(?:sobre|de)\s+(.*?)\s*\|\s*Qconcursos", title, re.IGNORECASE)
    nome = match_nome.group(1).strip() if match_nome else title
    
    # Tentar extrair quantidade do H2
    h2 = soup.select_one("h2.q-page-results-title")
    qtd_str = "0"
    if h2:
        txt = h2.get_text(strip=True)
        # Ex: "Foram encontradas70.672questões" ou "Foram encontradas 1.234 questões"
        match_qtd = re.search(r"encontradas?\s*([\d\.]+)", txt, re.IGNORECASE)
        if match_qtd:
            qtd_str = match_qtd.group(1)
        else:
            # Caso contenha apenas dígitos e pontos
            digits = re.findall(r"[\d\.]+", txt)
            if digits:
                qtd_str = digits[0]
                
    return nome, qtd_str, "OK"

def main():
    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p, headless=False)
        try:
            for id_disc in KNOWN_IDS[:8]:  # Testar primeiros 8
                url = f"https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]={id_disc}"
                aba.goto(url, timeout=60000)
                time.sleep(2)
                title = aba.title()
                html = aba.content()
                
                nome, qtd, status = parse_page(title, html)
                print(f"ID {id_disc:3d} | Nome: {nome:<45} | Qtd: {qtd:>10} | Status: {status}")
        finally:
            contexto.close()

if __name__ == "__main__":
    main()
