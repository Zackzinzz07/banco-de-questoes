"""Estilo FGV baseado no motor universal de Múltipla Escolha."""

from typing import Any, Dict, Optional

from .universal import EstiloMultiplaEscolha


class EstiloFGV(EstiloMultiplaEscolha):
    """Implementação compatível com FGV herdando do layout universal Múltipla Escolha."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.nome_oficial = "Fundação Getulio Vargas"
