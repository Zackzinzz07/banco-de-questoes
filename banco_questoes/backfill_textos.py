r"""Preenche texto-base e imagens das questões já coletadas.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe backfill_textos.py"""
from playwright.sync_api import sync_playwright

import db
import edital
import scraper_qc

con = db.conectar()
preenchidas = 0
with sync_playwright() as p:
    contexto, aba = scraper_qc.abrir_navegador(p)
    try:
        for materia in edital.nomes_materias():
            url_base = edital.MATERIAS[materia]["url_qc"]
            ultima = db.obter_progresso(con, materia)
            if not url_base or ultima == 0:
                continue
            for pagina in range(1, ultima + 1):
                aba.goto(scraper_qc.url_pagina(url_base, pagina))
                scraper_qc._pausa()
                novas = 0
                for q in scraper_qc.extrair_blocos(aba.content()):
                    if db.completar_texto_associado(con, q["id_qc"],
                                                    q["texto_associado"], q["imagens"]):
                        novas += 1
                preenchidas += novas
                print(f"[{materia}] página {pagina}: {novas} textos preenchidos")
    finally:
        contexto.close()
        con.close()
print(f"Pronto: {preenchidas} questões ganharam texto-base/imagem.")
