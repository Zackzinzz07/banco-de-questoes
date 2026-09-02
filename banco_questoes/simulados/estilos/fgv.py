"""
FGV (Fundação Getulio Vargas) specific styling implementation for exam documents.

This module provides the EstiloFGV class for rendering multiple choice exam questions
in the FGV format, featuring a 2-column layout with thin divider, high text density,
and special footer format with exam type and page number.

Classes:
    EstiloFGV: Concrete implementation of BaseBancaStyle for FGV exams.
"""

from typing import Dict, Any, List
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from .base import BaseBancaStyle


class EstiloFGV(BaseBancaStyle):
    """
    FGV-specific styling implementation for multiple choice exam questions.

    This class implements the visual style and layout requirements for FGV exams,
    which predominantly feature multiple choice question types with 5 alternatives
    (A, B, C, D, E) and extremely dense text content. The layout includes a 2-column
    structure with thin vertical divider, minimalist header with exam type indicator,
    and "TYPE X - PAGE Y" footer format.

    Characteristics:
    - Question type: Multiple Choice (5 alternatives: A, B, C, D, E)
    - Layout: 2 columns with thin continuous vertical line divider
    - Header: Clean header with "FGV CONHECIMENTO" and exam type (color/type indicator)
    - Footer: "TIPO 1 - PÁGINA X" format
    - Average question height: 11.0 cm (extremely large)
    - Text density: Extremely high with long case study enunciados
    - Margins: 2.0cm (top/bottom), 1.5cm (left/right)

    Example:
        >>> import yaml
        >>> from banco_questoes.configuracoes_bancas.fgv import config_dict
        >>> style = EstiloFGV(config_dict['fgv'])
        >>> # Use style.desenhar_cabecalho(), desenhar_rodape(), desenhar_questao()
    """

    # Constants for FGV styling
    LINHA_DIVISOR_PT = 0.3  # Thin vertical divider line width in points
    ALTURA_CABECALHO_CM = 2.0  # Header height in cm
    ALTURA_RODAPE_CM = 1.5  # Footer height in cm
    MARGEM_INTERNA_PT = 8  # Internal padding in points
    TIPO_PROVA_PADRAO = 1  # Default exam type for "TIPO X" format

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize EstiloFGV with FGV configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary from YAML containing
                FGV-specific styling, visual elements, and exam characteristics.

        Raises:
            ValueError: If required configuration keys are missing.
            TypeError: If config is not a dictionary.
        """
        super().__init__(config)

    def desenhar_cabecalho(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                          largura: float, altura: float) -> float:
        """
        Draw the FGV header with minimalist design and exam type indicator.

        The header consists of:
        - "FGV CONHECIMENTO" text (centered, left portion)
        - Exam type indicator (Type 1, 2, 3, 4) on the right
        - Clean, minimal design with adequate spacing

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

        # Draw FGV CONHECIMENTO text
        canvas_obj.setFont('Helvetica-Bold', 12)
        canvas_obj.setFillColor(colors.black)
        x_esquerda = x_inicio
        y_texto = y_base + altura_cabecalho_pt / 2 + 5
        canvas_obj.drawString(x_esquerda, y_texto, "FGV CONHECIMENTO")

        # Draw exam type indicator on the right
        x_direita = x_inicio + largura_cabecalho - 50
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.drawRightString(x_direita, y_texto, f"Tipo {self.TIPO_PROVA_PADRAO}")

        # Draw horizontal divider line
        canvas_obj.setLineWidth(0.5)
        canvas_obj.setStrokeColor(colors.black)
        canvas_obj.line(x_inicio, y_base, x_inicio + largura_cabecalho, y_base)

        return altura_cabecalho_pt

    def desenhar_rodape(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                       largura: float, altura: float) -> float:
        """
        Draw the FGV footer with "TIPO X - PÁGINA Y" format.

        The footer displays the exam type and page number in the format
        "TIPO X - PÁGINA Y" centered at the bottom of the page.

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

        # Draw page number in "TIPO X - PÁGINA Y" format
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.setFillColor(colors.black)
        numero_pagina_formatado = f"TIPO {self.TIPO_PROVA_PADRAO} - PÁGINA {pagina_numero}"
        canvas_obj.drawCentredString(x_centro, y_rodape, numero_pagina_formatado)

        return altura_rodape_pt

    def desenhar_questao(self, canvas_obj: canvas.Canvas, questao_data: Dict[str, Any],
                        posicao_x: float, posicao_y: float, largura_disponivel: float) -> float:
        """
        Draw a single FGV multiple choice question with 5 alternatives.

        The question layout includes:
        - Question number (bolded)
        - Question statement (enunciado) - often very long
        - Five response options: (A), (B), (C), (D), (E)

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            questao_data (Dict[str, Any]): Question data containing:
                - 'numero': int - Question number
                - 'enunciado': str - Question statement (often extremely long)
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

        # Set font for question number
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.setFillColor(colors.black)

        # Draw question number
        numero_str = f"{numero_questao}."
        canvas_obj.drawString(posicao_x, posicao_y, numero_str)

        # Get width of question number for text indentation
        largura_numero = canvas_obj.stringWidth(numero_str, 'Helvetica-Bold', 11)
        x_enunciado = posicao_x + largura_numero + self.MARGEM_INTERNA_PT

        # Draw question text (enunciado) - using Times for longer texts
        canvas_obj.setFont('Times-Roman', 10)
        altura_usada = self._desenhar_texto_quebrado(
            canvas_obj,
            enunciado,
            x_enunciado,
            posicao_y,
            largura_disponivel - (x_enunciado - posicao_x),
            tamanho_fonte=10,
            fonte='Times-Roman'
        )

        # Calculate position for answer options
        y_opcoes = posicao_y - altura_usada - self.MARGEM_INTERNA_PT

        # Draw response options: (A) (B) (C) (D) (E)
        canvas_obj.setFont('Helvetica', 10)
        opcoes_texto = "( ) A    ( ) B    ( ) C    ( ) D    ( ) E"
        canvas_obj.drawString(x_enunciado, y_opcoes, opcoes_texto)

        # Calculate total height used
        altura_total = altura_usada + self.MARGEM_INTERNA_PT + 15  # 15 points for options

        return altura_total

    def calcular_altura_questao(self, questao_data: Dict[str, Any],
                               largura_disponivel: float) -> float:
        """
        Calculate the height needed to render an FGV question.

        The calculation is based on:
        - The length of the question statement (enunciado) - often very long
        - The available width for text wrapping
        - A baseline height from configuration (11cm - extremely high)

        Args:
            questao_data (Dict[str, Any]): Question data (same structure as desenhar_questao).
            largura_disponivel (float): Available width in points.

        Returns:
            float: Calculated height needed in points.
        """
        enunciado = questao_data.get('enunciado', '')

        # Get baseline height from configuration (FGV has extremely high density)
        altura_media_cm = self.caracteristicas_prova.get('altura_media_questao_cm', 11.0)
        altura_base_pt = self.cm_para_pontos(altura_media_cm)

        # Calculate number of lines based on text length
        # Average characters per line at 10pt font, considering word breaks
        chars_por_linha = int(largura_disponivel / 6.0)  # Rough estimate
        numero_linhas = max(1, len(enunciado) // chars_por_linha + 1)

        # Estimate height: base height + additional space for text
        altura_texto = numero_linhas * 14  # 14 points per line
        altura_opcoes = 20  # Space for the A-E options

        altura_total = altura_base_pt + altura_texto + altura_opcoes

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
            >>> style = EstiloFGV(config)
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
            fonte (str): Font name (default: 'Times-Roman').

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
