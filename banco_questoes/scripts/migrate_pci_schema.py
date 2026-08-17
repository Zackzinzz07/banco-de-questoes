#!/usr/bin/env python
"""Migrate PCI schema to include hierarchical fields."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

def verificar_schema_pci():
    """Ensure PCI hierarchy columns exist."""
    try:
        con = psycopg2.connect('dbname=banco_questoes user=postgres host=localhost password=postgres')
        cur = con.cursor()

        print("Verificando schema PCI...")

        # Verificar se colunas existem
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'questoes'
            AND column_name IN ('categoria', 'subcategoria', 'tema', 'imagens_urls')
        """)
        existing = {row[0] for row in cur.fetchall()}

        needed = {'categoria', 'subcategoria', 'tema', 'imagens_urls'}
        missing = needed - existing

        if not missing:
            print("✅ Todas as colunas já existem")
            con.close()
            return

        print(f"Adicionando {len(missing)} colunas...")

        for col in sorted(missing):
            if col == 'imagens_urls':
                print(f"  - Adicionando {col} (JSONB)...")
                cur.execute(f"ALTER TABLE questoes ADD COLUMN {col} JSONB DEFAULT '[]'::jsonb")
            else:
                print(f"  - Adicionando {col} (VARCHAR)...")
                cur.execute(f"ALTER TABLE questoes ADD COLUMN {col} VARCHAR(255)")

        con.commit()
        print("✅ Schema migrado com sucesso!")
        con.close()

    except psycopg2.errors.DuplicateColumn:
        print("✅ Colunas já existem")
        con.close()
    except Exception as e:
        print(f"❌ Erro: {e}")
        raise

if __name__ == "__main__":
    verificar_schema_pci()
