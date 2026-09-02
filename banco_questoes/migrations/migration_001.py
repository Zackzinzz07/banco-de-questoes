"""Migration: Add cargo column to questoes table."""


def aplicar(con):
    """Apply migration: adds cargo column if not exists."""
    # Add cargo column if it doesn't exist
    try:
        con.execute("ALTER TABLE questoes ADD COLUMN IF NOT EXISTS cargo TEXT")
        con.commit()
    except Exception as e:
        con.rollback()
        print(f"Error adding cargo column: {e}")
        return False

    # Create index for cargo column
    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_cargo ON questoes(cargo)")
        con.commit()
        return True
    except Exception as e:
        con.rollback()
        print(f"Migration error: {e}")
        return False
