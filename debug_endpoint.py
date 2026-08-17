#!/usr/bin/env python
"""Debug PCI endpoint diretamente."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from banco_questoes import db
    from psycopg2.extras import RealDictCursor

    print("[TEST] Conectando ao PostgreSQL...")
    con = db.conectar()
    cur = con.cursor(cursor_factory=RealDictCursor)

    # Test 1: Count PCI
    print("[TEST] Contando questoes PCI...")
    cur.execute("SELECT COUNT(*) as total FROM questoes WHERE fonte = 'pci'")
    result = cur.fetchone()
    print(f"  ✓ Total PCI: {result['total']:,}")

    # Test 2: Categories
    print("[TEST] Listando categorias...")
    cur.execute("""
        SELECT DISTINCT categoria
        FROM questoes
        WHERE fonte = 'pci' AND categoria IS NOT NULL
        ORDER BY categoria
    """)
    cats = [row['categoria'] for row in cur.fetchall()]
    print(f"  ✓ Categorias: {len(cats)}")
    for cat in cats[:5]:
        print(f"     - {cat}")

    # Test 3: Try the query from endpoint
    print("[TEST] Executando query do endpoint...")
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

    print(f"  ✓ Por categoria: {len(por_categoria)}")

    # Test 4: Temas
    print("[TEST] Carregando temas...")
    for categoria in list(por_categoria.keys())[:2]:
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

        print(f"  ✓ {categoria}: {len(por_categoria[categoria]['temas'])} temas")

    con.close()

    print("\n[SUCCESS] Endpoint data está OK!")
    print(f"Total de categorias: {len(por_categoria)}")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
