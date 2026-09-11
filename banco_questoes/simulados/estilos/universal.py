"""Motor de diagramação e estilos universais para simulados de concurso.

Substitui os estilos dispersos por banca (Cebraspe, AOCP, FGV, IADES) por um
motor único de alta densidade e tipografia refinada, estruturado em 2 formatos:
1. Múltipla Escolha (A, B, C, D, E)
2. Certo e Errado (itens de julgamento)
"""

from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics

from . import alternativas
from .base import BaseBancaStyle

# Geometria A4 compacta
MARGEM_LATERAL_CM = 0.9  # 9mm lateral
MARGEM_SUPERIOR_CM = 1.0  # 10mm superior
MARGEM_INFERIOR_CM = 1.2  # 12mm inferior
CALHA_CM = 0.6  # 6mm entre colunas

# Tipografia
FONTE_CORPO = "Helvetica"
FONTE_NEGRITO = "Helvetica-Bold"
TAMANHO_CORPO_PT = 8.5
LEADING_CORPO_PT = 10.5

COR_TEXTO = colors.HexColor("#111111")
COR_METADADOS = colors.HexColor("#555555")
COR_LINHA_DIVISORIA = colors.HexColor("#333333")
COR_RODAPE = colors.HexColor("#666666")

TAMANHO_METADADOS_PT = 7.2
ALTURA_METADADOS_PT = 9.5
ESPACO_ENUNCIADO_OPCOES_PT = 3.0
ESPACO_ENTRE_OPCOES_PT = 2.0
ALTURA_MARCADOR_CE_PT = 10.0
ALTURA_DIVISOR_MATERIA_PT = 15.0
ALTURA_CABECALHO_P1_PT = 34.0

CONFIG_UNIVERSAL_PADRAO: Dict[str, Any] = {
    "nome_oficial": "Simulado Universal",
    "estilo_visual": {
        "fonte_titulo": "Helvetica 11pt",
        "fonte_corpo": "Helvetica 8.5pt",
        "layout_colunas": 2,
        "divisor_colunas": "Nenhum",
        "cores_dominantes": ["#111111", "#555555"],
        "elementos_graficos": {},
        "margens": {
            "superior_cm": MARGEM_SUPERIOR_CM,
            "inferior_cm": MARGEM_INFERIOR_CM,
            "esquerda_cm": MARGEM_LATERAL_CM,
            "direita_cm": MARGEM_LATERAL_CM,
        },
        "caixa_instrucoes": "Nenhuma",
    },
    "caracteristicas_prova": {
        "tipo_predominante": "Múltipla Escolha",
        "total_questoes_padrao": 60,
        "frase_antifraude_exemplo": "",
        "altura_media_questao_cm": 2.5,
        "densidade_texto": "Alta",
    },
    "estrutura_disciplinas_padrao": [],
}


def medir_largura(texto: str, fonte: str, tamanho: float) -> float:
    """Mede largura do texto de forma 100% determinística via métricas da fonte."""
    if not texto:
        return 0.0
    try:
        return float(pdfmetrics.stringWidth(texto, fonte, tamanho))
    except Exception:
        return float(len(texto)) * (tamanho * 0.52)


def quebrar_palavras_linha(
    palavras: List[str],
    largura_maxima: float,
    fonte: str,
    tamanho: float,
) -> List[List[str]]:
    if not palavras or largura_maxima <= 0:
        return []
    linhas: List[List[str]] = []
    linha_atual: List[str] = []
    largura_atual = 0.0
    espaco_w = medir_largura(" ", fonte, tamanho)

    for p in palavras:
        w_p = medir_largura(p, fonte, tamanho)
        if not linha_atual:
            linha_atual.append(p)
            largura_atual = w_p
        elif largura_atual + espaco_w + w_p <= largura_maxima:
            linha_atual.append(p)
            largura_atual += espaco_w + w_p
        else:
            linhas.append(linha_atual)
            linha_atual = [p]
            largura_atual = w_p
    if linha_atual:
        linhas.append(linha_atual)
    return linhas


def desenhar_linha_justificada(
    canvas_obj: Any,
    palavras: List[str],
    x: float,
    y: float,
    largura_maxima: float,
    fonte: str,
    tamanho: float,
    cor: Any,
    justificar: bool = True,
    is_last: bool = False,
) -> None:
    if not palavras:
        return
    canvas_obj.setFont(fonte, tamanho)
    canvas_obj.setFillColor(cor)

    if not justificar or is_last or len(palavras) <= 1:
        canvas_obj.drawString(x, y, " ".join(palavras))
        return

    largura_palavras = sum(medir_largura(p, fonte, tamanho) for p in palavras)
    normal_space = medir_largura(" ", fonte, tamanho)
    espaco_total_natural = largura_palavras + normal_space * (len(palavras) - 1)

    if espaco_total_natural < largura_maxima * 0.70:
        canvas_obj.drawString(x, y, " ".join(palavras))
        return

    gap = (largura_maxima - largura_palavras) / (len(palavras) - 1)
    if gap > normal_space * 2.8:
        canvas_obj.drawString(x, y, " ".join(palavras))
        return

    cur_x = x
    for p in palavras:
        canvas_obj.drawString(cur_x, y, p)
        cur_x += medir_largura(p, fonte, tamanho) + gap


class EstiloUniversal(BaseBancaStyle):
    """Estilo universal de alta densidade e diagramação precisa em 2 colunas."""

    tipo_formato: str = "multipla_escolha"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = dict(CONFIG_UNIVERSAL_PADRAO)
        if config and isinstance(config, dict):
            cfg.update(config)
            if "estilo_visual" in config:
                cfg["estilo_visual"] = dict(CONFIG_UNIVERSAL_PADRAO["estilo_visual"])
                cfg["estilo_visual"].update(config["estilo_visual"])
            if "caracteristicas_prova" in config:
                cfg["caracteristicas_prova"] = dict(
                    CONFIG_UNIVERSAL_PADRAO["caracteristicas_prova"]
                )
                cfg["caracteristicas_prova"].update(config["caracteristicas_prova"])
        super().__init__(cfg)

    def obter_margens_cm(self) -> Dict[str, float]:
        return {
            "superior": MARGEM_SUPERIOR_CM,
            "inferior": MARGEM_INFERIOR_CM,
            "esquerda": MARGEM_LATERAL_CM,
            "direita": MARGEM_LATERAL_CM,
        }

    def desenhar_cabecalho(
        self,
        canvas_obj: Any,
        pagina_numero: int,
        largura: float,
        altura: float,
        info_concurso: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Desenha cabeçalho EXCLUSIVAMENTE na Página 1."""
        if pagina_numero != 1:
            return 0.0

        margens = self.obter_margens_pontos()
        x_inicio = margens["esquerda"]
        x_fim = largura - margens["direita"]
        largura_total = x_fim - x_inicio
        y_cursor = altura - margens["superior"]

        info = info_concurso or {}
        titulo = (
            info.get("concurso_nome")
            or info.get("orgao")
            or self.config.get("nome_oficial")
            or "SIMULADO DE TREINO"
        ).strip()
        cargo = (info.get("cargo") or "").strip()

        # 1. Título do Concurso / Órgão em Negrito
        canvas_obj.setFont(FONTE_NEGRITO, 11.0)
        canvas_obj.setFillColor(COR_TEXTO)
        while titulo and medir_largura(titulo, FONTE_NEGRITO, 11.0) > largura_total:
            titulo = titulo[:-4] + "..."
        canvas_obj.drawString(x_inicio, y_cursor - 10.0, titulo)

        # 2. Subtítulo (Cargo / Informações do Simulado)
        canvas_obj.setFont(FONTE_CORPO, 8.5)
        canvas_obj.setFillColor(COR_METADADOS)
        subtitulo = (
            f"Cargo: {cargo}  •  Simulado Preparatório"
            if cargo
            else "Simulado Preparatório"
        )
        while subtitulo and medir_largura(subtitulo, FONTE_CORPO, 8.5) > largura_total:
            subtitulo = subtitulo[:-4] + "..."
        canvas_obj.drawString(x_inicio, y_cursor - 21.0, subtitulo)

        # 3. Linha divisória horizontal sutil
        canvas_obj.setLineWidth(0.6)
        canvas_obj.setStrokeColor(COR_LINHA_DIVISORIA)
        y_linha = y_cursor - 26.0
        canvas_obj.line(x_inicio, y_linha, x_fim, y_linha)
        return ALTURA_CABECALHO_P1_PT

    def desenhar_rodape(
        self, canvas_obj: Any, pagina_numero: int, largura: float, altura: float
    ) -> float:
        """Rodapé minimalista: apenas o número da página no canto inferior direito."""
        margens = self.obter_margens_pontos()
        x_direita = largura - margens["direita"]
        canvas_obj.setFont(FONTE_CORPO, 8.0)
        canvas_obj.setFillColor(COR_RODAPE)
        num_str = str(pagina_numero)
        num_w = medir_largura(num_str, FONTE_CORPO, 8.0)
        canvas_obj.drawString(x_direita - num_w, 15.0, num_str)
        return 0.0

    def desenhar_divisor_materia(
        self,
        canvas_obj: Any,
        materia: str,
        x: float,
        y: float,
        largura: float,
        fonte: str = FONTE_NEGRITO,
    ) -> float:
        if not materia:
            return 0.0
        canvas_obj.setFont(fonte, 9.0)
        canvas_obj.setFillColor(COR_TEXTO)
        canvas_obj.drawString(x, y - 8.5, materia.strip().upper())
        canvas_obj.setLineWidth(0.5)
        canvas_obj.setStrokeColor(colors.HexColor("#888888"))
        canvas_obj.line(x, y - 11.5, x + largura, y - 11.5)
        return ALTURA_DIVISOR_MATERIA_PT

    def altura_divisor_materia(self, materia: str = "") -> float:
        return ALTURA_DIVISOR_MATERIA_PT if materia else 0.0

    def _resolver_formato(self, questao_data: Dict[str, Any]) -> str:
        formato = questao_data.get("formato")
        if formato:
            return str(formato).lower().strip()
        if questao_data.get("opcoes"):
            return "multipla_escolha"
        return self.tipo_formato

    def _preparar_linhas_enunciado(
        self, numero: int, enunciado: str, largura: float
    ) -> Tuple[str, float, List[List[str]]]:
        prefixo = f"QUESTÃO {numero}. "
        w_prefix = medir_largura(prefixo, FONTE_NEGRITO, TAMANHO_CORPO_PT)
        palavras = enunciado.strip().split()
        if not palavras:
            return prefixo, w_prefix, []

        espaco_w = medir_largura(" ", FONTE_CORPO, TAMANHO_CORPO_PT)
        linhas: List[List[str]] = []
        linha_atual: List[str] = []
        largura_atual = w_prefix

        for p in palavras:
            w_p = medir_largura(p, FONTE_CORPO, TAMANHO_CORPO_PT)
            if not linha_atual:
                if largura_atual + w_p <= largura:
                    linha_atual.append(p)
                    largura_atual += w_p
                else:
                    linhas.append([])
                    linha_atual = [p]
                    largura_atual = w_p
            elif largura_atual + espaco_w + w_p <= largura:
                linha_atual.append(p)
                largura_atual += espaco_w + w_p
            else:
                linhas.append(linha_atual)
                linha_atual = [p]
                largura_atual = w_p
        if linha_atual:
            linhas.append(linha_atual)
        return prefixo, w_prefix, linhas

    def _preparar_linhas_opcao(
        self, letra: str, texto: str, largura: float
    ) -> Tuple[str, float, List[List[str]]]:
        prefixo = f"({letra}) "
        w_prefix = medir_largura(prefixo, FONTE_NEGRITO, TAMANHO_CORPO_PT)
        palavras = texto.strip().split()
        largura_util = max(10.0, largura - w_prefix)
        linhas = quebrar_palavras_linha(palavras, largura_util, FONTE_CORPO, TAMANHO_CORPO_PT)
        return prefixo, w_prefix, linhas

    def calcular_altura_questao(self, questao_data: Dict[str, Any], largura: float) -> float:
        numero = questao_data.get("numero", 0)
        enunciado = questao_data.get("enunciado", "")
        formato = self._resolver_formato(questao_data)
        opcoes = questao_data.get("opcoes") or []

        altura_origem = ALTURA_METADADOS_PT
        _, _, linhas_enunc = self._preparar_linhas_enunciado(numero, enunciado, largura)
        altura_enunc = max(1, len(linhas_enunc)) * LEADING_CORPO_PT

        if formato == "certo_errado":
            altura_opcoes = ALTURA_MARCADOR_CE_PT
        else:
            if opcoes:
                altura_opcoes = 0.0
                for op in opcoes:
                    _, _, linhas_op = self._preparar_linhas_opcao(
                        op.get("letra", ""), op.get("texto", ""), largura
                    )
                    altura_opcoes += (
                        max(1, len(linhas_op)) * LEADING_CORPO_PT
                    ) + ESPACO_ENTRE_OPCOES_PT
            else:
                altura_opcoes = ALTURA_MARCADOR_CE_PT

        return altura_origem + altura_enunc + ESPACO_ENUNCIADO_OPCOES_PT + altura_opcoes

    def desenhar_questao(
        self,
        canvas_obj: Any,
        questao_data: Dict[str, Any],
        posicao_x: float,
        posicao_y: float,
        largura: float,
    ) -> float:
        numero = questao_data.get("numero", 0)
        enunciado = questao_data.get("enunciado", "")
        formato = self._resolver_formato(questao_data)
        opcoes = questao_data.get("opcoes") or []
        y_cursor = posicao_y

        # 1. Metadados de procedência
        texto_origem = alternativas.formatar_origem(questao_data)
        canvas_obj.setFont(FONTE_CORPO, TAMANHO_METADADOS_PT)
        canvas_obj.setFillColor(COR_METADADOS)
        while (
            texto_origem
            and medir_largura(texto_origem, FONTE_CORPO, TAMANHO_METADADOS_PT) > largura
        ):
            texto_origem = texto_origem[:-4] + "..."
        canvas_obj.drawString(posicao_x, y_cursor - 6.5, texto_origem)
        y_cursor -= ALTURA_METADADOS_PT

        # 2. Enunciado
        prefixo_num, w_prefix, linhas_enunc = self._preparar_linhas_enunciado(
            numero, enunciado, largura
        )

        for i, palavras in enumerate(linhas_enunc):
            y_linha = y_cursor - (i * LEADING_CORPO_PT) - 7.0
            is_last = i == len(linhas_enunc) - 1

            if i == 0:
                canvas_obj.setFont(FONTE_NEGRITO, TAMANHO_CORPO_PT)
                canvas_obj.setFillColor(COR_TEXTO)
                canvas_obj.drawString(posicao_x, y_linha, prefixo_num)

                largura_disp_l0 = max(10.0, largura - w_prefix)
                desenhar_linha_justificada(
                    canvas_obj,
                    palavras,
                    posicao_x + w_prefix,
                    y_linha,
                    largura_disp_l0,
                    FONTE_CORPO,
                    TAMANHO_CORPO_PT,
                    COR_TEXTO,
                    justificar=True,
                    is_last=is_last,
                )
            else:
                desenhar_linha_justificada(
                    canvas_obj,
                    palavras,
                    posicao_x,
                    y_linha,
                    largura,
                    FONTE_CORPO,
                    TAMANHO_CORPO_PT,
                    COR_TEXTO,
                    justificar=True,
                    is_last=is_last,
                )

        altura_enunc = max(1, len(linhas_enunc)) * LEADING_CORPO_PT
        y_cursor -= altura_enunc + ESPACO_ENUNCIADO_OPCOES_PT

        # 3. Alternativas / Julgamento
        if formato == "certo_errado":
            canvas_obj.setFont(FONTE_CORPO, TAMANHO_CORPO_PT)
            canvas_obj.setFillColor(COR_TEXTO)
            canvas_obj.drawString(posicao_x, y_cursor - 7.0, "( ) Certo    ( ) Errado")
            altura_opcoes = ALTURA_MARCADOR_CE_PT
        else:
            if opcoes:
                altura_opcoes = 0.0
                for op in opcoes:
                    pref_op, w_pref_op, linhas_op = self._preparar_linhas_opcao(
                        op.get("letra", ""), op.get("texto", ""), largura
                    )
                    y_opcao_base = y_cursor - altura_opcoes

                    for j, pal_op in enumerate(linhas_op):
                        y_linha_op = y_opcao_base - (j * LEADING_CORPO_PT) - 7.0
                        is_last_op = j == len(linhas_op) - 1

                        if j == 0:
                            canvas_obj.setFont(FONTE_NEGRITO, TAMANHO_CORPO_PT)
                            canvas_obj.setFillColor(COR_TEXTO)
                            canvas_obj.drawString(posicao_x, y_linha_op, pref_op)

                        desenhar_linha_justificada(
                            canvas_obj,
                            pal_op,
                            posicao_x + w_pref_op,
                            y_linha_op,
                            largura - w_pref_op,
                            FONTE_CORPO,
                            TAMANHO_CORPO_PT,
                            COR_TEXTO,
                            justificar=True,
                            is_last=is_last_op,
                        )

                    qtd = max(1, len(linhas_op))
                    altura_opcoes += (qtd * LEADING_CORPO_PT) + ESPACO_ENTRE_OPCOES_PT
            else:
                canvas_obj.setFont(FONTE_CORPO, TAMANHO_CORPO_PT)
                canvas_obj.setFillColor(COR_TEXTO)
                canvas_obj.drawString(
                    posicao_x, y_cursor - 7.0, "( ) A    ( ) B    ( ) C    ( ) D    ( ) E"
                )
                altura_opcoes = ALTURA_MARCADOR_CE_PT

        return (
            ALTURA_METADADOS_PT + altura_enunc + ESPACO_ENUNCIADO_OPCOES_PT + altura_opcoes
        )


class EstiloMultiplaEscolha(EstiloUniversal):
    """Estilo universal para simulados de Múltipla Escolha."""

    tipo_formato: str = "multipla_escolha"


class EstiloCertoErrado(EstiloUniversal):
    """Estilo universal para simulados de Certo / Errado (Julgar Itens)."""

    tipo_formato: str = "certo_errado"
