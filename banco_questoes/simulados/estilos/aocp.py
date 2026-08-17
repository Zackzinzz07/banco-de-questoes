"""
AOCP (Instituto AOCP) specific styling implementation for exam documents.

This module provides the EstiloAOCP class for rendering multiple choice exam questions
in the AOCP format, featuring a 2-column layout without divider, gray numbered boxes
for questions, and clean footer format.

Classes:
    EstiloAOCP: Concrete implementation of BaseBancaStyle for AOCP exams.
"""

from typing import Dict, Any, List
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from .base import BaseBancaStyle


class EstiloAOCP(BaseBancaStyle):
    """
    AOCP-specific styling implementation for multiple choice exam questions.

    This class implements the visual style and layout requirements for AOCP exams,
    which predominantly feature multiple choice question types with 5 alternatives
    (A, B, C, D, E). The layout includes a 2-column structure without divider,
    gray numbered boxes for question numbers, and clean footer with proof code and page.

    Characteristics:
    - Question type: Multiple Choice (5 alternatives: A, B, C, D, E)
    - Layout: 2 columns without divider (1.0cm spacing between columns)
    - Question style: Gray numbered boxes for question numbers
    - Header: AOCP logo left, contract agency logo right
    - Footer: Proof code and sequential page numbering
    - Average question height: 7.5 cm
    - Text density: Medium with objective statements and analytical items
    - Margins: 1.5cm (uniform)

    Example:
        >>> import yaml
        >>> from banco_questoes.configuracoes_bancas.aocp import config_dict
        >>> style = EstiloAOCP(config_dict['instituto_aocp'])
        >>> # Use style.desenhar_cabecalho(), desenhar_rodape(), desenhar_questao()
    """

    # Constants for AOCP styling
    ESPACAMENTO_COLUNAS_CM = 1.0  # Column spacing without divider
    ALTURA_CABECALHO_CM = 1.5  # Header height in cm
    ALTURA_RODAPE_CM = 1.0  # Footer height in cm
    MARGEM_INTERNA_PT = 6  # Internal padding in points
    TAMANHO_BOX_NUMERO_PT = 20  # Gray box size for question number in points
    CODIGO_PROVA_PADRAO = "001"  # Default proof code

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize EstiloAOCP with AOCP configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary from YAML containing
                AOCP-specific styling, visual elements, and exam characteristics.

        Raises:
            ValueError: If required configuration keys are missing.
            TypeError: If config is not a dictionary.
        """
        super().__init__(config)

    def desenhar_cabecalho(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                          largura: float, altura: float) -> float:
        """
        Draw the AOCP header with logos and clean design.

        The header consists of:
        - AOCP logo placeholder on the left
        - Contract agency logo placeholder on the right
        - Minimal design with clean spacing

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            pagina_numero (int): Current page number (1-indexed).
            largura (float): Page width in points.
            altura (float): Page height in points.

        Returns:
            float: Height occupied by the header in points.
        """
        margens = self.obter_margens_pontos()
        altura_cabecalho_pt = self.cm_para_pontos(self.ALTURA_CABECALHO_CM)

        # Calculate header coordinates
        x_inicio = margens['esquerda']
        y_base = altura - margens['superior'] - altura_cabecalho_pt
        largura_cabecalho = largura - margens['esquerda'] - margens['direita']

        # Draw AOCP logo placeholder (left side)
        canvas_obj.setFont('Helvetica-Bold', 10)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.drawString(x_inicio, y_base + altura_cabecalho_pt / 2, "AOCP")

        # Draw Agency logo placeholder (right side)
        x_direita = x_inicio + largura_cabecalho - 50
        canvas_obj.drawRightString(x_direita, y_base + altura_cabecalho_pt / 2, "Orgao")

        # Draw separator line
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(x_inicio, y_base, x_inicio + largura_cabecalho, y_base)

        return altura_cabecalho_pt

    def desenhar_rodape(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                       largura: float, altura: float) -> float:
        """
        Draw the AOCP footer with proof code and page number.

        The footer displays the proof code and sequential page number in a clean
        format centered at the bottom of the page.

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            pagina_numero (int): Current page number (1-indexed).
            largura (float): Page width in points.
            altura (float): Page height in points.

        Returns:
            float: Height occupied by the footer in points.
        """
        margens = self.obter_margens_pontos()
        altura_rodape_pt = self.cm_para_pontos(self.ALTURA_RODAPE_CM)

        # Calculate footer coordinates (centered at bottom)
        x_centro = largura / 2
        y_rodape = margens['inferior'] + self.MARGEM_INTERNA_PT

        # Draw proof code and page number
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(colors.black)
        footer_text = f"Prova {self.CODIGO_PROVA_PADRAO} - Página {pagina_numero}"
        canvas_obj.drawCentredString(x_centro, y_rodape, footer_text)

        return altura_rodape_pt

    def desenhar_questao(self, canvas_obj: canvas.Canvas, questao_data: Dict[str, Any],
                        posicao_x: float, posicao_y: float, largura_disponivel: float) -> float:
        """
        Draw a single AOCP multiple choice question with gray numbered box.

        The question layout includes:
        - Gray box with question number (bolded inside box)
        - Question statement (enunciado)
        - Five response options: (A), (B), (C), (D), (E)

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            questao_data (Dict[str, Any]): Question data containing:
                - 'numero': int - Question number
                - 'enunciado': str - Question statement
                - 'opcoes': list - Answer options (A, B, C, D, E)
                - 'tipo': str - Question type (should be "MC" for Multiple Choice)
            posicao_x (float): X position in points.
            posicao_y (float): Y position in points.
            largura_disponivel (float): Available width in points.

        Returns:
            float: Height occupied by the question in points.
        """
        numero_questao = questao_data.get('numero', 0)
        enunciado = questao_data.get('enunciado', '')

        # Draw gray box for question number
        tamanho_box = self.TAMANHO_BOX_NUMERO_PT
        x_box = posicao_x
        y_box = posicao_y - tamanho_box / 2

        # Draw gray rectangle background
        canvas_obj.setFillColor(colors.HexColor('#CCCCCC'))  # Light gray
        canvas_obj.rect(x_box, y_box - tamanho_box, tamanho_box, tamanho_box, fill=True, stroke=True)

        # Draw question number inside gray box
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.setFillColor(colors.black)
        x_numero = x_box + tamanho_box / 2
        y_numero = y_box - tamanho_box / 2 - 4  # Vertical center adjustment
        canvas_obj.drawCentredString(x_numero, y_numero, str(numero_questao))

        # Calculate position for enunciado (after the box)
        x_enunciado = posicao_x + tamanho_box + self.MARGEM_INTERNA_PT
        y_enunciado = posicao_y

        # Draw question text (enunciado)
        canvas_obj.setFont('Helvetica', 10)
        altura_usada = self._desenhar_texto_quebrado(
            canvas_obj,
            enunciado,
            x_enunciado,
            y_enunciado,
            largura_disponivel - (x_enunciado - posicao_x),
            tamanho_fonte=10,
            fonte='Helvetica'
        )

        # Calculate position for answer options
        y_opcoes = y_enunciado - altura_usada - self.MARGEM_INTERNA_PT

        # Draw response options: (A) (B) (C) (D) (E)
        canvas_obj.setFont('Helvetica', 10)
        opcoes_texto = "( ) A    ( ) B    ( ) C    ( ) D    ( ) E"
        canvas_obj.drawString(x_enunciado, y_opcoes, opcoes_texto)

        # Calculate total height used
        altura_total = altura_usada + self.MARGEM_INTERNA_PT + 20  # 20 points for box and options

        return altura_total

    def calcular_altura_questao(self, questao_data: Dict[str, Any],
                               largura_disponivel: float) -> float:
        """
        Calculate the height needed to render an AOCP question.

        The calculation is based on:
        - The length of the question statement (enunciado)
        - The available width for text wrapping
        - A baseline height from configuration
        - The gray numbered box size

        Args:
            questao_data (Dict[str, Any]): Question data (same structure as desenhar_questao).
            largura_disponivel (float): Available width in points.

        Returns:
            float: Calculated height needed in points.
        """
        enunciado = questao_data.get('enunciado', '')

        # Get baseline height from configuration
        altura_media_cm = self.caracteristicas_prova.get('altura_media_questao_cm', 7.5)
        altura_base_pt = self.cm_para_pontos(altura_media_cm)

        # Calculate number of lines based on text length
        # Average characters per line at 10pt font, considering word breaks
        chars_por_linha = int(largura_disponivel / 6.0)  # Rough estimate
        numero_linhas = max(1, len(enunciado) // chars_por_linha + 1)

        # Estimate height: base height + additional space for text
        altura_texto = numero_linhas * 14  # 14 points per line
        altura_box_numero = self.TAMANHO_BOX_NUMERO_PT + 5  # Box plus margin
        altura_opcoes = 20  # Space for the A-E options

        altura_total = altura_base_pt + altura_texto + altura_box_numero + altura_opcoes

        return altura_total

    def _quebrar_texto(self, texto: str, largura_maxima_pt: float,
                      tamanho_fonte: int = 10) -> List[str]:
        """
        Break text into multiple lines to fit within a maximum width.

        This helper method implements simple text wrapping based on character width
        estimation. It respects word boundaries when possible.

        Args:
            texto (str): Text to break into lines.
            largura_maxima_pt (float): Maximum width in points.
            tamanho_fonte (int): Font size in points (default: 10).

        Returns:
            List[str]: List of text lines that fit within the maximum width.

        Example:
            >>> style = EstiloAOCP(config)
            >>> lines = style._quebrar_texto("A long text...", 200, tamanho_fonte=10)
            >>> for line in lines:
            ...     print(line)
        """
        if not texto or largura_maxima_pt <= 0:
            return []

        # Rough estimate: average character width is ~0.6 * font size in points
        char_width_estimate = tamanho_fonte * 0.6
        chars_per_line = int(largura_maxima_pt / char_width_estimate)

        # Ensure at least some characters per line
        if chars_per_line < 1:
            chars_per_line = 1

        linhas = []
        palavras = texto.split()

        linha_atual = ""
        for palavra in palavras:
            # Check if adding this word would exceed the limit
            teste_linha = f"{linha_atual} {palavra}".strip()
            if len(teste_linha) <= chars_per_line:
                linha_atual = teste_linha
            else:
                # Word doesn't fit, save current line and start new one
                if linha_atual:
                    linhas.append(linha_atual)
                linha_atual = palavra

        # Add the last line
        if linha_atual:
            linhas.append(linha_atual)

        return linhas if linhas else [""]

    def _desenhar_texto_quebrado(self, canvas_obj: canvas.Canvas, texto: str,
                                 x: float, y: float, largura_maxima_pt: float,
                                 tamanho_fonte: int = 10,
                                 fonte: str = 'Helvetica') -> float:
        """
        Helper method to draw text with automatic line wrapping.

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            texto (str): Text to draw.
            x (float): X position in points.
            y (float): Y position in points.
            largura_maxima_pt (float): Maximum width in points.
            tamanho_fonte (int): Font size in points (default: 10).
            fonte (str): Font name (default: 'Open-Sans').

        Returns:
            float: Total height occupied by the text in points.
        """
        canvas_obj.setFont(fonte, tamanho_fonte)
        canvas_obj.setFillColor(colors.black)

        linhas = self._quebrar_texto(texto, largura_maxima_pt, tamanho_fonte)
        linha_height = tamanho_fonte * 1.4  # Line height with some leading

        for i, linha in enumerate(linhas):
            y_linha = y - (i * linha_height)
            canvas_obj.drawString(x, y_linha, linha)

        altura_total = len(linhas) * linha_height
        return altura_total
