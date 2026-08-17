#!/usr/bin/env python
"""Verificar se categoria foi salva."""

import psycopg2

con = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
cur = con.cursor()

# Verificar categoria NULL
cur.execute("""
    SELECT COUNT(*) FROM questoes
    WHERE fonte = 'pci' AND categoria IS NULL
""")
print(f"PCI com categoria NULL: {cur.fetchone()[0]:,}")

# Verificar categoria NOT NULL
cur.execute("""
    SELECT COUNT(*) FROM questoes
    WHERE fonte = 'pci' AND categoria IS NOT NULL
""")
print(f"PCI com categoria preenchida: {cur.fetchone()[0]:,}")

# Ver alguns exemplos
print("\nExemplos de questoes PCI:")
cur.execute("""
    SELECT id, categoria, tema, materia, fonte
    FROM questoes
    WHERE fonte = 'pci'
    LIMIT 5
""")

for row in cur.fetchall():
    print(f"  ID: {row[0]}, Categoria: {row[1]}, Tema: {row[2]}, Materia: {row[3]}")

con.close()
