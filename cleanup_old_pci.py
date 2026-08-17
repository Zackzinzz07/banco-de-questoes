#!/usr/bin/env python
"""Limpar questões PCI antigas (NULL categoria) da re-coleta."""

import psycopg2

con = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
cur = con.cursor()

print("Limpando questoes PCI antigas (NULL categoria)...")

# Contar antes
cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci' AND categoria IS NULL")
antes = cur.fetchone()[0]
print(f"  Antes: {antes:,} questoes com categoria NULL")

# Deletar
cur.execute("DELETE FROM questoes WHERE fonte='pci' AND categoria IS NULL")
con.commit()

# Contar depois
cur.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci'")
depois = cur.fetchone()[0]

print(f"  Deletadas: {antes:,}")
print(f"  Apos limpeza: {depois:,} questoes PCI validas")

# Verificar dados apos limpeza
cur.execute("""
    SELECT categoria, COUNT(*)
    FROM questoes
    WHERE fonte='pci' AND categoria IS NOT NULL
    GROUP BY categoria
    ORDER BY count DESC
    LIMIT 5
""")

print("\nTop 5 categorias PCI (apos limpeza):")
for cat, cnt in cur.fetchall():
    print(f"  {cat:40} {cnt:6,}")

con.close()
print("\n[DONE] Limpeza concluida!")
