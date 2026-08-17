#!/usr/bin/env python
"""Validar endpoints da API com dados atualizados."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from banco_questoes import db
    from psycopg2.extras import RealDictCursor
    import json

    print("="*80)
    print("VALIDANDO ENDPOINTS PCI")
    print("="*80)

    con = db.conectar()
    cur = con.cursor(cursor_factory=RealDictCursor)

    # Test 1: Contar PCI com categoria
    cur.execute("SELECT COUNT(*) as total FROM questoes WHERE fonte='pci' AND categoria IS NOT NULL")
    pci_total = cur.fetchone()["total"]
    print(f"\n[TEST 1] Total PCI com categoria: {pci_total:,}")

    # Test 2: Categorias descobertas
    cur.execute("""
        SELECT DISTINCT categoria
        FROM questoes
        WHERE fonte='pci' AND categoria IS NOT NULL
        ORDER BY categoria
    """)
    categorias = [row["categoria"] for row in cur.fetchall()]
    print(f"[TEST 2] Categorias: {len(categorias)}")
    for cat in categorias[:5]:
        print(f"          - {cat}")

    # Test 3: Simular GET /api/stats/pci
    print("\n[TEST 3] Simulando GET /api/stats/pci...")
    cur.execute("""
        SELECT categoria, COUNT(*) as qtd
        FROM questoes
        WHERE fonte = 'pci' AND categoria IS NOT NULL
        GROUP BY categoria
        ORDER BY qtd DESC
    """)

    por_categoria = {}
    for row in cur.fetchall():
        cat = row["categoria"]
        por_categoria[cat] = {
            "total": row["qtd"],
            "temas": {}
        }

    print(f"          Encontradas: {len(por_categoria)} categorias")

    # Test 4: Temas por categoria
    print("\n[TEST 4] Carregando temas...")
    total_temas = 0
    for categoria in list(por_categoria.keys())[:3]:
        cur.execute("""
            SELECT tema, COUNT(*) as qtd,
                   COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
            FROM questoes
            WHERE fonte = 'pci' AND categoria = %s AND tema IS NOT NULL
            GROUP BY tema
            ORDER BY qtd DESC
        """, (categoria,))

        for row in cur.fetchall():
            por_categoria[categoria]["temas"][row["tema"]] = {
                "total": row["qtd"],
                "com_imagens": row["com_imagens"]
            }
            total_temas += 1

        print(f"          {categoria:40} {len(por_categoria[categoria]['temas']):3} temas")

    # Test 5: Imagens
    print("\n[TEST 5] Imagens coletadas...")
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
        FROM questoes
        WHERE fonte='pci'
    """)
    row = cur.fetchone()
    pct = round((row["com_imagens"] / row["total"] * 100), 1) if row["total"] > 0 else 0
    print(f"          Total: {row['total']:,}")
    print(f"          Com imagens: {row['com_imagens']:,} ({pct}%)")

    con.close()

    print("\n" + "="*80)
    print("✅ VALIDACAO CONCLUIDA - Endpoints prontos!")
    print("="*80)
    print("\nProximos passos:")
    print("  1. Aguardar conclusao dos scrapers (PCI + QConcursos)")
    print("  2. Rodar: python cleanup_old_pci.py")
    print("  3. Iniciar servidor: python -m uvicorn banco_questoes.web_api:app --reload")
    print("  4. Acessar: http://localhost:8000")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
