"""Script de Varredura e Mapeamento de Disciplinas do QConcursos.

Itera IDs numéricos de disciplina no QConcursos (ex: 1 a 600) via URL de filtro:
https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]=NNN

Extrai:
- ID da Disciplina
- Nome da Disciplina (via <title> e DOM)
- Quantidade de Questões (via h2.q-page-results-title)

Salva o resultado em CSV e JSON incrementalmente para permitir retomada.
Pausa de 2 a 3 segundos entre requisições.
Interrompe imediatamente se detectar Cloudflare, Captcha ou tela de login.
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
import scraper_qc

CSV_OUT = ROOT_DIR / "estudo_autonomo" / "mapeamento_disciplinas_qc.csv"
JSON_OUT = ROOT_DIR / "estudo_autonomo" / "mapeamento_disciplinas_qc.json"

def carregar_progresso() -> dict[int, dict]:
    results = {}
    if JSON_OUT.exists():
        try:
            with open(JSON_OUT, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    results[item["id"]] = item
        except Exception as e:
            print(f"Aviso ao carregar JSON existente: {e}")
    return results

def salvar_progresso(results: dict[int, dict]):
    lista = [results[k] for k in sorted(results.keys())]
    
    # Salvar JSON
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
        
    # Salvar CSV
    with open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "nome", "quantidade_questoes", "status"])
        for item in lista:
            writer.writerow([item["id"], item["nome"], item["quantidade_questoes"], item["status"]])

def extrair_dados_disciplina(title: str, html: str) -> tuple[str | None, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Verificar bloqueios reais / Cloudflare / Login
    title_lower = title.lower()
    
    if "just a moment" in title_lower or "um momento" in title_lower or "attention required" in title_lower:
        return None, "0", "BLOQUEADO_CLOUDFLARE"
        
    if soup.select_one("#challenge-running, #challenge-form, #turnstile-wrapper, .cf-turnstile"):
        return None, "0", "BLOQUEADO_CLOUDFLARE"
        
    if "entrar" in title_lower and "login" in title_lower:
        return None, "0", "REQUER_LOGIN"
        
    # 2. Verificar se a página é a página padrão sem filtro (ID inválido/inexistente)
    if "provas, aulas e questões" in title_lower and "sobre" not in title_lower and "de " not in title_lower:
        return None, "0", "NAO_ENCONTRADO"
        
    # 3. Extrair nome da disciplina do título
    # Exemplos:
    # "Questões de Concurso sobre Português | Qconcursos.com"
    # "Questões de Concurso de Noções de Informática | Qconcursos.com"
    nome = None
    match_nome = re.search(r"(?:questões de concurso[s]?\s+(?:sobre|de)|sobre)\s+(.*?)\s*\|\s*Qconcursos", title, re.IGNORECASE)
    if match_nome:
        nome = match_nome.group(1).strip()
    else:
        # Tentar no summary tag da página se o título não tiver a estrutura esperada
        tag = soup.select_one(".q-summary-tag")
        if tag:
            txt_tag = tag.get_text(strip=True)
            if txt_tag.startswith("Disciplina"):
                nome = txt_tag.replace("Disciplina", "").strip()

    if not nome or nome.lower() in ["questões", "concursos públicos"]:
        return None, "0", "NAO_ENCONTRADO"
        
    # 4. Extrair quantidade de questões
    h2 = soup.select_one("h2.q-page-results-title")
    qtd_str = "0"
    if h2:
        txt_h2 = h2.get_text(strip=True)
        # Ex: "Foram encontradas70.672questões"
        match_qtd = re.search(r"encontradas?\s*([\d\.]+)", txt_h2, re.IGNORECASE)
        if match_qtd:
            qtd_str = match_qtd.group(1).replace(".", "")
        else:
            digits = re.findall(r"[\d\.]+", txt_h2)
            if digits:
                qtd_str = digits[0].replace(".", "")
                
    return nome, qtd_str, "OK"

def main():
    parser = argparse.ArgumentParser(description="Mapeador de disciplinas QConcursos")
    parser.add_argument("--inicio", type=int, default=1, help="ID inicial (padrão: 1)")
    parser.add_argument("--fim", type=int, default=600, help="ID final (padrão: 600)")
    parser.add_argument("--forcar", action="store_true", help="Re-checar IDs já mapeados")
    args = parser.parse_args()

    results = carregar_progresso()
    print(f"Carregados {len(results)} registros anteriores.")

    with sync_playwright() as p:
        contexto, aba = scraper_qc.abrir_navegador(p, headless=False)
        try:
            for id_disc in range(args.inicio, args.fim + 1):
                if not args.forcar and id_disc in results and results[id_disc]["status"] == "OK":
                    continue
                    
                url = f"https://www.qconcursos.com/questoes-de-concursos/questoes?discipline_ids[]={id_disc}"
                try:
                    aba.goto(url, timeout=60000)
                except Exception as e:
                    print(f"⚠️ Erro ao carregar ID {id_disc}: {e}")
                    results[id_disc] = {"id": id_disc, "nome": None, "quantidade_questoes": "0", "status": "ERRO_HTTP"}
                    salvar_progresso(results)
                    continue

                # Pausa aleatória entre 2.0 e 3.0s como exigido
                time.sleep(random.uniform(2.0, 3.0))

                title = aba.title()
                html = aba.content()

                nome, qtd_str, status = extrair_dados_disciplina(title, html)

                if status in ("BLOQUEADO_CLOUDFLARE", "REQUER_LOGIN"):
                    print(f"\n❌ INTERROMPIDO no ID {id_disc}: {status}")
                    print("Por favor, resolva o desafio ou login na janela do navegador e execute novamente.")
                    break

                results[id_disc] = {
                    "id": id_disc,
                    "nome": nome,
                    "quantidade_questoes": qtd_str,
                    "status": status
                }

                if status == "OK":
                    print(f"[ID {id_disc:3d}] ✅ {nome:<40} | Qtd: {qtd_str:>10} questões")
                else:
                    print(f"[ID {id_disc:3d}] ⚪ {status}")

                salvar_progresso(results)

        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário. Progresso salvo!")
        finally:
            salvar_progresso(results)
            contexto.close()
            print(f"Mapeamento concluído/interrompido. Total de registros: {len(results)}")

if __name__ == "__main__":
    main()
