"""Estilo IADES baseado no motor universal de Múltipla Escolha."""

from typing import Any, Dict, Optional

from .universal import EstiloMultiplaEscolha


class EstiloIADES(EstiloMultiplaEscolha):
    """Implementação compatível com IADES herdando do layout universal Múltipla Escolha."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.nome_oficial = "Instituto Americano de Desenvolvimento"
