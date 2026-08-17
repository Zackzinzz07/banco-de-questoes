import pytest
import db
import config


@pytest.fixture(autouse=True)
def banco_de_teste(request, monkeypatch):
    """
    Monkeypatch DATABASE_URL to test DB and truncate before each test.

    This fixture is skipped for test_gerador_multibanca.py tests since they
    don't require PostgreSQL connectivity.
    """
    # Skip this fixture for multi-banca tests
    if "test_gerador_multibanca" in request.node.nodeid:
        yield
        return

    # For other tests, try to connect to PostgreSQL
    try:
        monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)
        con = db.conectar()
        try:
            con.execute("TRUNCATE questoes, progresso_scraper RESTART IDENTITY CASCADE")
            con.commit()
        finally:
            con.close()
    except Exception:
        # If PostgreSQL is not available, just yield without setup
        pass

    yield
