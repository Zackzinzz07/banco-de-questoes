"""
Pytest configuration for banco_questoes tests.

This module provides pytest fixtures for testing both database-dependent
and database-independent tests.
"""
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


# ============================================================================
# Database Fixture (from parent conftest)
# ============================================================================

@pytest.fixture(autouse=True)
def banco_de_teste(monkeypatch):
    """Redireciona TODO teste para o banco de teste e limpa antes de cada um.

    Sem exceções por arquivo: `test_gerador_multibanca` já foi isento daqui
    (por ser todo mockado) e, ao virar teste de integração de verdade, passou
    a gravar questões falsas no banco de PRODUÇÃO.

    O redirecionamento acontece fora do try: se ficasse dentro, uma falha de
    conexão deixaria os testes apontando para produção silenciosamente.
    """
    import config
    import db

    monkeypatch.setattr(db, "DATABASE_URL", config.TEST_DATABASE_URL)

    try:
        con = db.conectar()
    except Exception:
        yield  # Postgres indisponível: testes que não usam banco seguem
        return

    try:
        con.execute("TRUNCATE questoes, progresso_scraper RESTART IDENTITY CASCADE")
    finally:
        con.close()

    yield


# ============================================================================
# Multi-banca Test Fixtures
# ============================================================================

@pytest.fixture
def config_paths() -> Dict[str, Path]:
    """
    Provide paths to all 4 banca configuration YAML files.

    Note: Quadrix não está implementado — SEDES usa gerar_simulado.py.

    Returns:
        Dict[str, Path]: Dictionary mapping banca names to config file paths.
    """
    base_dir = Path(__file__).resolve().parent.parent / "configuracoes_bancas"
    return {
        "cebraspe": base_dir / "cebraspe.yaml",
        "iades": base_dir / "iades.yaml",
        "fgv": base_dir / "fgv.yaml",
        "aocp": base_dir / "aocp.yaml",
    }


@pytest.fixture
def configs(config_paths: Dict[str, Path]) -> Dict[str, Dict[str, Any]]:
    """
    Load all 5 banca configuration YAML files into memory.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping banca names to config dicts.
    """
    configs = {}
    for banca_name, config_path in config_paths.items():
        with open(config_path, 'r', encoding='utf-8') as f:
            configs[banca_name] = yaml.safe_load(f)
    return configs


@pytest.fixture
def questao_fake():
    """
    Fixture that returns a factory function for creating fake questao objects.

    Returns:
        callable: Function that creates questao dicts for testing.
    """
    def _questao_fake(i: int, materia: str = "Língua Portuguesa") -> Dict[str, Any]:
        """Create a fake questao for testing."""
        return {
            "id_qc": f"Q{i}",
            "enunciado": f"Enunciado de teste número {i}: assinale a alternativa correta. Texto com < & > para escapar.",
            "alternativas": {
                "A": "Opção A",
                "B": "Opção B",
                "C": "Opção C",
                "D": "Opção D",
                "E": "Opção E"
            },
            "gabarito": "B" if i % 2 else None,
            "comentario": "Comentário da questão." if i == 1 else None,
            "materia": materia,
            "assunto": None,
            "banca": "Instituto Quadrix",
            "orgao": "SEDES/DF",
            "ano": 2026,
            "prova": None,
            "fonte": "qconcursos",
        }
    return _questao_fake
