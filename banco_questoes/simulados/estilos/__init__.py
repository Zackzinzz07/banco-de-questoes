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

# Placeholder imports for banca-specific styles (to be implemented in Tasks 3-4)
# CebraspeStyle = None  # Task 3
# IadesStyle = None     # Task 3
# QuadrixStyle = None   # Task 3
# FgvStyle = None       # Task 4
# AocpStyle = None      # Task 4

__all__ = [
    'BaseBancaStyle',
    # 'CebraspeStyle',
    # 'IadesStyle',
    # 'QuadrixStyle',
    # 'FgvStyle',
    # 'AocpStyle',
]
