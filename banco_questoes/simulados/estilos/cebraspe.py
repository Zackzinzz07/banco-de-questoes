"""Estilo Cebraspe baseado no motor universal de Certo/Errado."""

from typing import Any, Dict, Optional

from .universal import EstiloCertoErrado


class EstiloCebraspe(EstiloCertoErrado):
    """Implementação compatível com Cebraspe herdando do layout universal C/E."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.nome_oficial = (
            "Centro Brasileiro de Pesquisa em Avaliação e Seleção e de Promoção de Eventos"
        )
