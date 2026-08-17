#!/usr/bin/env python
"""Inspeciona estrutura HTML do PCI para descobrir seletores CSS corretos."""

import requests
from bs4 import BeautifulSoup
import json

def inspecionar_pagina_simulados():
    """Inspecciona a página principal de simulados para descobrir estrutura."""
    url = "https://www.pciconcursos.com.br/simulados/"

    print("\n" + "="*80)
    print("🔍 INSPECIONANDO: https://www.pciconcursos.com.br/simulados/")
    print("="*80)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Salvar HTML inteiro para análise
        with open("pci_simulados_full.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("\n✅ HTML salvo em: pci_simulados_full.html")

        # Procurar por padrões comuns
        print("\n" + "-"*80)
        print("ANÁLISE DE ESTRUTURA:")
        print("-"*80)

        # Buscar divs com "categoria", "simulado", "subject", etc
        for classe in ["categoria", "simulado", "subject", "subject-item", "quiz", "bloco", "section"]:
            elementos = soup.find_all(class_=classe)
            if elementos:
                print(f"\n✓ Encontrado: .{classe} ({len(elementos)} elementos)")
                for i, el in enumerate(elementos[:2]):
                    print(f"  [{i}] {str(el)[:150]}...")

        # Procurar por IDs
        print("\n" + "-"*80)
        print("IDs ENCONTRADOS:")
        print("-"*80)
        todos_com_id = soup.find_all(id=True)
        ids_unicos = set(el.get("id") for el in todos_com_id)
        for id_val in sorted(ids_unicos)[:20]:
            print(f"  - #{id_val}")

        # Procurar por estrutura de listas aninhadas
        print("\n" + "-"*80)
        print("ESTRUTURA DE LISTAS:")
        print("-"*80)

        listas = soup.find_all(["ul", "ol"])
        print(f"Encontradas {len(listas)} listas (<ul> ou <ol>)")

        for i, lista in enumerate(listas[:3]):
            items = lista.find_all("li", recursive=False)
            print(f"\n  Lista {i}: {len(items)} items diretos")
            for j, item in enumerate(items[:2]):
                txt = item.get_text(strip=True)[:60]
                print(f"    [{j}] {txt}...")

        # Procurar por links com padrão de categoria/tema
        print("\n" + "-"*80)
        print("LINKS COM PADRÃO /simulados/xxx:")
        print("-"*80)

        links = soup.find_all("a", href=True)
        simulado_links = [
            (el.get_text(strip=True), el["href"])
            for el in links
            if "/simulados/" in el["href"] and el.get_text(strip=True)
        ]

        print(f"\nEncontrados {len(simulado_links)} links de simulados")

        # Agrupar por padrão
        categorias = {}
        for texto, href in simulado_links:
            partes = href.split("/simulados/")[-1].strip("/").split("/")
            if partes[0] not in categorias:
                categorias[partes[0]] = []
            categorias[partes[0]].append((texto, href, partes))

        print("\nCATEGORIAS DESCOBERTAS:")
        for cat, items in sorted(categorias.items())[:5]:
            print(f"\n  📂 {cat}:")
            for texto, href, partes in items[:3]:
                print(f"     └─ {texto}")
                print(f"        href: {href}")
                print(f"        partes: {partes}")

        # Procurar por números (contagem de questões)
        print("\n" + "-"*80)
        print("ANÁLISE DE NÚMEROS (contagem de questões):")
        print("-"*80)

        import re
        todos_textos = soup.get_text()
        numeros = re.findall(r'\d+\s*questões?', todos_textos)
        print(f"\nEncontradas {len(set(numeros))} contagens únicas de questões:")
        for num in sorted(set(numeros))[:10]:
            print(f"  - {num}")

        # Procurar padrão específico (categoria com subcategorias)
        print("\n" + "-"*80)
        print("PROCURANDO PADRÃO: Categoria → Subcategoria:")
        print("-"*80)

        # Tentar encontrar h2/h3/h4 que possam ser categorias
        headers = soup.find_all(["h2", "h3", "h4"])
        print(f"\nEncontrados {len(headers)} headers (h2-h4)")

        categoria_atual = None
        for header in headers[:15]:
            texto = header.get_text(strip=True)
            if len(texto) > 5 and len(texto) < 100:
                print(f"  {header.name}: {texto}")

                # Procurar próximo elemento que possa ser subcategoria
                prox = header.find_next_sibling()
                if prox and prox.name in ["ul", "ol", "div"]:
                    items = prox.find_all(["li", "a"], recursive=False)[:2]
                    for item in items:
                        item_texto = item.get_text(strip=True)[:60]
                        print(f"      └─ {item_texto}")

        print("\n" + "="*80)
        print("✅ Análise completa! Verifique pci_simulados_full.html para mais detalhes")
        print("="*80 + "\n")

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspecionar_pagina_simulados()
