"""Estilos universais e compatibilidade com bancas examinadoras."""

from .aocp import EstiloAOCP
from .base import BaseBancaStyle
from .cebraspe import EstiloCebraspe
from .fgv import EstiloFGV
from .iades import EstiloIADES
from .universal import EstiloCertoErrado, EstiloMultiplaEscolha, EstiloUniversal

__all__ = [
    "BaseBancaStyle",
    "EstiloUniversal",
    "EstiloMultiplaEscolha",
    "EstiloCertoErrado",
    "EstiloCebraspe",
    "EstiloIADES",
    "EstiloFGV",
    "EstiloAOCP",
]
