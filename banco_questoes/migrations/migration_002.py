"""Migration: Add banca, orgao, and cargo columns to questoes table."""


def aplicar(con):
    """Apply migration: adds banca, orgao, cargo columns if not exist."""
    try:
        con.execute("ALTER TABLE questoes ADD COLUMN IF NOT EXISTS banca TEXT")
        con.execute("ALTER TABLE questoes ADD COLUMN IF NOT EXISTS orgao TEXT")
        con.execute("ALTER TABLE questoes ADD COLUMN IF NOT EXISTS cargo TEXT")
        con.commit()
        print("✅ Colunas banca, orgao, cargo adicionadas")
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao adicionar colunas: {e}")
        return False

    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_banca ON questoes(banca)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_orgao ON questoes(orgao)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_questoes_cargo ON questoes(cargo)")
        con.commit()
        print("✅ Índices criados")
        return True
    except Exception as e:
        con.rollback()
        print(f"❌ Erro ao criar índices: {e}")
        return False
