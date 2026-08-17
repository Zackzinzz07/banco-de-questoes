#!/usr/bin/env python
"""Monitor progress da coleta PCI."""

import psycopg2

con = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
cur = con.cursor()

# Total geral
cur.execute('SELECT COUNT(*) FROM questoes')
total = cur.fetchone()[0]

# PCI
cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte = 'pci'")
pci = cur.fetchone()[0]

# Por categoria
cur.execute("""
    SELECT categoria, COUNT(*) as qtd
    FROM questoes
    WHERE fonte = 'pci' AND categoria IS NOT NULL
    GROUP BY categoria
    ORDER BY qtd DESC
    LIMIT 10
""")

print("\n" + "="*80)
print("MONITORAR COLETA PCI")
print("="*80)
print(f"\nTotal de questoes: {total:,}")
print(f"PCI coletadas: {pci:,}")

print("\nTop 10 categorias:")
for cat, qtd in cur.fetchall():
    print(f"  {cat:40} {qtd:6,}")

con.close()
print("\n")
