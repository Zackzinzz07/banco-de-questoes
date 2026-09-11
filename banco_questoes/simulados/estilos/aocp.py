"""Estilo AOCP baseado no motor universal de Múltipla Escolha."""

from typing import Any, Dict, Optional

from .universal import EstiloMultiplaEscolha


class EstiloAOCP(EstiloMultiplaEscolha):
    """Implementação compatível com AOCP herdando do layout universal Múltipla Escolha."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.nome_oficial = "Instituto AOCP"
