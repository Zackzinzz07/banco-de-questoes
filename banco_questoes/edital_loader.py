"""Dynamic edital loader with YAML support and fallback to hardcoded configs."""

import os
from pathlib import Path
from typing import Optional, Dict, List
import yaml

# Try to import the hardcoded edital for fallback
try:
    from banco_questoes import edital as edital_hardcoded
except ImportError:
    edital_hardcoded = None


# Path to YAML configuration directory
EDITAIS_DIR = Path(__file__).parent / "configuracoes_editais"

# Cache for loaded editais
_editais_cache: Dict[str, Optional[Dict]] = {}


def _carregar_yaml(concurso: str) -> Optional[Dict]:
    """Load YAML file for a concurso, returns dict or None."""
    yaml_path = EDITAIS_DIR / f"{concurso}.yaml"

    if not yaml_path.exists():
        return None

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except Exception:
        return None


def _fallback_sedes_df() -> Optional[Dict]:
    """Fallback to hardcoded SEDES/DF edital if YAML not found."""
    if edital_hardcoded is None:
        return None

    # Build edital dict from hardcoded module
    return {
        "sedes_df": {
            "nome": "Edital nº 1/2026 SEDES/DF - Técnico de Atendimento Direto ao Cidadão",
            "banca": "Instituto Quadrix",
            "ano": 2026,
            "orgao": "Secretaria de Estado de Desenvolvimento Social e Transferência de Renda",
            "formato": "Multipla_Escolha",
            "total_questoes": 60,
            "tempo_minutos": 120,
            "cargos": {
                "Técnico de Atendimento Direto ao Cidadão": {
                    "nivel": "médio",
                    "materias": edital_hardcoded.PESOS,
                }
            },
        }
    }


def listar_concursos() -> List[str]:
    """Return list of available concursos (sorted)."""
    esperados = {
        "sedes_df",
        "prf",
        "bacen",
        "receita_federal",
        "inss",
        "correios",
        "banco_brasil",
    }

    # Check which YAML files exist
    disponíveis = set()
    for concurso in esperados:
        yaml_path = EDITAIS_DIR / f"{concurso}.yaml"
        if yaml_path.exists():
            disponíveis.add(concurso)

    # If SEDES/DF not found in YAML but fallback available, include it
    if "sedes_df" not in disponíveis and edital_hardcoded is not None:
        disponíveis.add("sedes_df")

    return sorted(list(disponíveis))


def carregar_edital(concurso: str) -> Optional[Dict]:
    """
    Load full YAML config for concurso.
    Returns dict with structure: {concurso_key: {config...}} or None if not found.
    Fallback to hardcoded edital.py for SEDES/DF if YAML doesn't exist.
    """
    # Check cache first
    if concurso in _editais_cache:
        return _editais_cache[concurso]

    # Try to load from YAML
    yaml_data = _carregar_yaml(concurso)
    if yaml_data is not None:
        edital_dict = yaml_data.get(concurso)
        _editais_cache[concurso] = edital_dict
        return edital_dict

    # Fallback to hardcoded for SEDES/DF
    if concurso == "sedes_df" and edital_hardcoded is not None:
        fallback_data = _fallback_sedes_df()
        if fallback_data:
            edital_dict = fallback_data.get("sedes_df")
            _editais_cache[concurso] = edital_dict
            return edital_dict

    # Not found
    _editais_cache[concurso] = None
    return None


def listar_cargos(concurso: str) -> List[str]:
    """Return list of cargo names for concurso."""
    edital = carregar_edital(concurso)
    if edital is None or "cargos" not in edital:
        return []

    return sorted(list(edital["cargos"].keys()))


def obter_materias(concurso: str, cargo: str) -> Optional[Dict]:
    """
    Return materias dict for a concurso/cargo.
    Structure: {materia_name: {pesos: int, assuntos: [list]}}
    """
    edital = carregar_edital(concurso)
    if edital is None or "cargos" not in edital:
        return None

    if cargo not in edital["cargos"]:
        return None

    cargo_config = edital["cargos"][cargo]
    if "materias" not in cargo_config:
        return None

    # Convert simple materias dict to structured format
    materias_simples = cargo_config["materias"]
    materias_estruturadas = {}

    for materia_nome, pesos_value in materias_simples.items():
        materias_estruturadas[materia_nome] = {
            "pesos": pesos_value,
            "assuntos": [],  # Will be filled if data available
        }

    return materias_estruturadas


def obter_pesos(concurso: str, cargo: str) -> Dict[str, int]:
    """Return {materia: questoes_count, ...} for allocation."""
    materias = obter_materias(concurso, cargo)
    if materias is None:
        return {}

    return {materia: dados["pesos"] for materia, dados in materias.items()}


def distribuir_por_peso(quantidade: int, pesos: Dict[str, int]) -> Dict[str, int]:
    """
    Allocate total questions by weight (proportional distribution).
    Ensures exact sum equals quantidade.
    """
    if not pesos:
        return {}

    total_pesos = sum(pesos.values())
    if total_pesos == 0:
        return {m: 0 for m in pesos}

    # Calculate proportional allocation
    exatas = {m: quantidade * p / total_pesos for m, p in pesos.items()}
    dist = {m: int(v) for m, v in exatas.items()}

    # Distribute remainder to subjects with highest fractional parts
    sobra = quantidade - sum(dist.values())
    if sobra > 0:
        # Get fractional parts
        fracoes = {m: exatas[m] - dist[m] for m in exatas}
        # Sort by fractional part (highest first)
        ordem = sorted(fracoes, key=lambda m: fracoes[m], reverse=True)
        # Distribute remainder
        for m in ordem[:sobra]:
            dist[m] += 1

    return dist


def obter_assuntos(concurso: str, cargo: str, materia: str) -> List[str]:
    """
    Return assuntos (topics) list for a subject.
    Currently returns empty list (placeholder for future data).
    """
    materias = obter_materias(concurso, cargo)
    if materias is None or materia not in materias:
        return []

    return materias[materia].get("assuntos", [])
