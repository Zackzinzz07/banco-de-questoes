import pytest
import db
import config


@pytest.fixture(autouse=True)
def banco_de_teste(monkeypatch):
    """Monkeypatch DATABASE_URL to test DB and truncate before each test."""
    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
    con = db.conectar()
    try:
        con.execute("TRUNCATE questoes, progresso_scraper RESTART IDENTITY CASCADE")
        con.commit()
    finally:
        con.close()
    yield
