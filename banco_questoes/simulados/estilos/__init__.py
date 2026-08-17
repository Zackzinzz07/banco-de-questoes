"""
Estilos de simulados para diferentes bancas examinadoras.

This package provides banca-specific styling implementations for exam documents.
Each banca (exam board) has its own visual style, layout, and formatting rules.

Available styles:
    - BaseBancaStyle: Abstract base class for all banca styles
    - CebraspeStyle: Cebraspe (Centro Brasileiro de Pesquisa) specific styling
    - IadesStyle: IADES (Instituto Americano de Desenvolvimento) specific styling
    - QuadrixStyle: Quadrix (Instituto Quadrix) specific styling
    - FgvStyle: FGV (Fundação Getulio Vargas) specific styling
    - AocpStyle: AOCP (Instituto AOCP) specific styling

Example:
    >>> from banco_questoes.simulados.estilos import BaseBancaStyle
    >>> # Load configuration and create style instance
    >>> config = yaml.safe_load(open('configuracoes_bancas/cebraspe.yaml'))
    >>> # style = CebraspeStyle(config)  # Task 3-4
"""

from .base import BaseBancaStyle
from .cebraspe import EstiloCebraspe
from .iades import EstiloIADES
from .quadrix import EstiloQuadrix
from .fgv import EstiloFGV
from .aocp import EstiloAOCP

__all__ = [
    'BaseBancaStyle',
    'EstiloCebraspe',
    'EstiloIADES',
    'EstiloQuadrix',
    'EstiloFGV',
    'EstiloAOCP',
]
