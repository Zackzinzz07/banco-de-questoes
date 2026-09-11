"""Migration: Add formato column to questoes table.

Distingue Certo/Errado (Cebraspe, Quadrix) de Múltipla Escolha (demais
bancas) — sem isso, `sortear_questoes` não sabe filtrar e o motor de PDF
acaba desenhando alternativas A-E num layout Cebraspe.
"""


def aplicar(con):
    """Apply migration: adds formato column, index and backfill if not exist."""
    try:
        con.execute(
            "ALTER TABLE questoes ADD COLUMN IF NOT EXISTS formato TEXT DEFAULT 'multipla_escolha'"
        )
        con.commit()
        print("✅ Coluna formato adicionada")
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao adicionar coluna formato: {e}")
        return False

    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_formato ON questoes(formato)")
        con.commit()
        print("✅ Índice de formato criado")
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao criar índice: {e}")
        return False

    # Backfill: alternativas sem a chave "D" não é múltipla escolha (que
    # sempre tem A-D no mínimo) — é C/E, com no máximo "C" e "E", ou vazia.
    # Mesma regra usada em db._inferir_formato() para questão nova.
    try:
        con.execute(
            "UPDATE questoes SET formato = 'certo_errado' WHERE NOT (alternativas::jsonb ? 'D')"
        )
        con.commit()
        print("✅ Backfill de formato aplicado")
        return True
    except Exception as e:
        con.rollback()
        print(f"❌ Erro no backfill de formato: {e}")
        return False
