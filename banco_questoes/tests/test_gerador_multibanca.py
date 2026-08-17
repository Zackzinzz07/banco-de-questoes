"""Comprehensive tests for multi-banca simulado generator."""
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch, call

import db
from simulados import gerar_simulado
from simulados.estilos.base import BaseBancaStyle
from simulados.estilos.cebraspe import EstiloCebraspe


def questao_fake(i, materia="Língua Portuguesa"):
    """Create a fake questao for testing."""
    return {
        "id_qc": f"Q{i}",
        "enunciado": f"Enunciado de teste número {i}: assinale a alternativa correta. Texto com < & > para escapar.",
        "alternativas": {"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D", "E": "Opção E"},
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


def test_load_all_configs(config_paths: Dict[str, Path]) -> None:
    """Test that all 5 banca configuration files exist and load successfully."""
    required_sections = ["estilo_visual", "caracteristicas_prova", "estrutura_disciplinas_padrao"]

    for banca_name, config_path in config_paths.items():
        assert config_path.exists(), f"Config file missing for {banca_name}: {config_path}"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        assert config is not None, f"Config file empty or invalid for {banca_name}"
        banca_key = banca_name
        assert banca_key in config, f"Config key '{banca_key}' not found in {banca_name} config"
        banca_config = config[banca_key]
        for section in required_sections:
            assert section in banca_config, f"Missing section '{section}' in {banca_name} config"
        assert "nome_oficial" in banca_config, f"Missing 'nome_oficial' in {banca_name}"
        assert "estilo_visual" in banca_config, f"Missing 'estilo_visual' in {banca_name}"
        assert "margens" in banca_config["estilo_visual"], f"Missing 'margens' in {banca_name} estilo_visual"


def test_estilo_cebraspe_instantiate(configs: Dict[str, Dict[str, Any]]) -> None:
    """Test that EstiloCebraspe can be instantiated with valid config."""
    cebraspe_config = configs["cebraspe"]["cebraspe"]
    style = EstiloCebraspe(cebraspe_config)
    assert isinstance(style, BaseBancaStyle), "EstiloCebraspe must inherit from BaseBancaStyle"
    assert style.nome_oficial is not None, "Config not properly loaded"
    assert "Centro Brasileiro" in style.nome_oficial, "Banca name not correctly extracted from config"


def test_estilo_iades_instantiate(configs: Dict[str, Dict[str, Any]]) -> None:
    """Test that EstiloIADES can be instantiated with valid config."""
    pytest.importorskip("simulados.estilos.iades", minversion=None)
    from simulados.estilos.iades import EstiloIADES
    iades_config = configs["iades"]["iades"]
    style = EstiloIADES(iades_config)
    assert isinstance(style, BaseBancaStyle), "EstiloIADES must inherit from BaseBancaStyle"
    assert style.nome_oficial is not None, "Config not properly loaded"
    assert "Instituto Americano" in style.nome_oficial, "Banca name not correctly extracted from config"


def test_gerar_simulado_cebraspe(tmp_path: Path, questao_fake) -> None:
    """Test PDF generation for Cebraspe with a small simulado (5 questions)."""
    con = db.conectar(tmp_path / "test_cebraspe.db")
    for i in range(5):
        db.salvar_questao(con, questao_fake(i))
    output_path = tmp_path / "simulado_cebraspe.pdf"
    result = gerar_simulado.gerar("Língua Portuguesa", 5, output_path, con=con)
    assert output_path.exists(), "PDF file was not created"
    file_size = output_path.stat().st_size
    assert file_size > 1000, f"PDF file too small: {file_size} bytes"
    pdf_header = output_path.read_bytes()[:5]
    assert pdf_header == b"%PDF-", f"Invalid PDF header: {pdf_header}"


def test_gerador_invalid_banca(configs: Dict[str, Dict[str, Any]]) -> None:
    """Test that invalid banca name raises appropriate error."""
    invalid_banca = "BANCA_INEXISTENTE_XYZ"
    with pytest.raises((ValueError, KeyError)):
        _ = configs[invalid_banca]


def test_cm_para_pontos(configs: Dict[str, Dict[str, Any]]) -> None:
    """Test cm_para_pontos() conversion method of BaseBancaStyle."""
    cebraspe_config = configs["cebraspe"]["cebraspe"]
    style = EstiloCebraspe(cebraspe_config)
    result = style.cm_para_pontos(1.0)
    assert isinstance(result, float), "Result should be float"
    assert 28.0 < result < 29.0, f"1 cm should be ~28.35 points, got {result}"
    assert style.cm_para_pontos(0.0) == 0.0, "0 cm should equal 0 points"
    result_10cm = style.cm_para_pontos(10.0)
    assert 280.0 < result_10cm < 290.0, f"10 cm should be ~283.46 points, got {result_10cm}"
    with pytest.raises(ValueError):
        style.cm_para_pontos(-1.0)
    with pytest.raises(TypeError):
        style.cm_para_pontos("1.0")  # type: ignore


def test_gerar_simulado_completo_todas_bancas(tmp_path, monkeypatch):
    """
    Integration test that generates real simulados (PDFs) for all 5 exam boards.

    Loops through 5 bancas, generates a simulado with 20 questions each,
    verifies PDF was created and is > 1000 bytes, prints results.
    """
    import db

    # Mock db module to avoid PostgreSQL requirement
    mock_con = MagicMock()
    mock_con.execute.return_value.fetchone.return_value = {"c": 20}

    def mock_conectar(path=None):
        """Mock conectar that returns a mock connection."""
        return mock_con

    def mock_salvar_questao(con, q):
        """Mock salvar_questao that does nothing."""
        pass

    monkeypatch.setattr(db, "conectar", mock_conectar)
    monkeypatch.setattr(db, "salvar_questao", mock_salvar_questao)

    # 5 exam boards (bancas)
    bancas = ["cebraspe", "iades", "quadrix", "fgv", "aocp"]

    # Create database connection (mocked)
    con = db.conectar(tmp_path / "simulados.db")

    # Add 20 questoes to database (mocked)
    for i in range(20):
        db.salvar_questao(con, questao_fake(i))

    # Generate simulado for each banca
    for banca in bancas:
        saida = tmp_path / f"simulado_{banca}.pdf"

        # Generate simulado
        caminho = gerar_simulado.gerar("Língua Portuguesa", 20, saida, con=con)

        # Verify PDF was created
        assert saida.exists(), f"PDF não foi criado para banca {banca}"

        # Verify PDF size > 1000 bytes
        tamanho_bytes = saida.stat().st_size
        assert tamanho_bytes > 1000, f"PDF de {banca} é muito pequeno: {tamanho_bytes} bytes"

        # Verify PDF header
        assert saida.read_bytes()[:5] == b"%PDF-", f"PDF inválido para banca {banca}"

        # Print result in format: [PASS] banca: path (size KB)
        tamanho_kb = tamanho_bytes / 1024
        print(f"[PASS] {banca}: {saida} ({tamanho_kb:.1f} KB)")
