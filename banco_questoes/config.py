"""Environment configuration for database connection."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/banco_questoes"
)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/banco_questoes_test"
)

COLETA_DISPONIVEL = os.environ.get("COLETA_DISPONIVEL", "1") == "1"
