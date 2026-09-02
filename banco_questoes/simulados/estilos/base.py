"""
Base abstract class for exam board (banca) styling in exam documents.

This module provides the BaseBancaStyle abstract class that defines the interface
for creating specialized style implementations for different exam boards (Cebraspe,
IADES, Quadrix, FGV, AOCP).

Classes:
    BaseBancaStyle: Abstract base class for banca-specific styling and document rendering.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import yaml
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


class BaseBancaStyle(ABC):
    """
    Abstract base class for exam board (banca) specific styling.

    This class provides the foundation for creating specialized style implementations
    for different Brazilian exam boards (Cebraspe, IADES, Quadrix, FGV, AOCP).

    Subclasses must implement:
    - desenhar_cabecalho(): Draw the document header
    - desenhar_rodape(): Draw the document footer
    - desenhar_questao(): Draw a single question
    - calcular_altura_questao(): Calculate question height based on content

    Concrete methods provided:
    - obter_estilos_paragraph(): Get styled ParagraphStyle objects
    - cm_para_pontos(): Convert centimeters to ReportLab points
    """

    # ReportLab conversion constants
    CM_TO_POINTS = 28.346456692913385  # 1 cm = 28.346... points

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize BaseBancaStyle with configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary loaded from YAML.
                Expected structure:
                {
                    'nome_oficial': str,
                    'estilo_visual': {
                        'fonte_titulo': str,
                        'fonte_corpo': str,
                        'layout_colunas': int,
                        'divisor_colunas': str,
                        'cores_dominantes': List[str],
                        'elementos_graficos': Dict,
                        'margens': Dict,
                        'caixa_instrucoes': str
                    },
                    'caracteristicas_prova': {
                        'tipo_predominante': str,
                        'total_questoes_padrao': int,
                        'frase_antifraude_exemplo': str,
                        'altura_media_questao_cm': float,
                        'densidade_texto': str
                    },
                    'estrutura_disciplinas_padrao': List[Dict]
                }

        Raises:
            ValueError: If required configuration keys are missing.
            TypeError: If config is not a dictionary.
        """
        if not isinstance(config, dict):
            raise TypeError(f"config must be a dictionary, got {type(config)}")

        # Validate required keys
        required_keys = {'estilo_visual', 'caracteristicas_prova', 'estrutura_disciplinas_padrao'}
        if not required_keys.issubset(config.keys()):
            missing = required_keys - set(config.keys())
            raise ValueError(f"Missing required configuration keys: {missing}")

        self.config = config
        self.nome_oficial = config.get('nome_oficial', 'Unnamed Banca')
        self.estilo_visual = config.get('estilo_visual', {})
        self.caracteristicas_prova = config.get('caracteristicas_prova', {})
        self.estrutura_disciplinas = config.get('estrutura_disciplinas_padrao', [])

    @abstractmethod
    def desenhar_cabecalho(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                          largura: float, altura: float) -> float:
        """
        Draw the document header on the current page.

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            pagina_numero (int): Current page number (1-indexed).
            largura (float): Page width in points.
            altura (float): Page height in points.

        Returns:
            float: Height occupied by the header in points.
        """
        pass

    @abstractmethod
    def desenhar_rodape(self, canvas_obj: canvas.Canvas, pagina_numero: int,
                       largura: float, altura: float) -> float:
        """
        Draw the document footer on the current page.

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            pagina_numero (int): Current page number (1-indexed).
            largura (float): Page width in points.
            altura (float): Page height in points.

        Returns:
            float: Height occupied by the footer in points.
        """
        pass

    @abstractmethod
    def desenhar_questao(self, canvas_obj: canvas.Canvas, questao_data: Dict[str, Any],
                        posicao_x: float, posicao_y: float, largura_disponivel: float) -> float:
        """
        Draw a single question on the page.

        Args:
            canvas_obj (canvas.Canvas): ReportLab Canvas object for drawing.
            questao_data (Dict[str, Any]): Question data containing:
                - 'numero': int - Question number
                - 'enunciado': str - Question statement
                - 'opcoes': List[Dict] - Answer options
                - 'tipo': str - Question type
            posicao_x (float): X position in points.
            posicao_y (float): Y position in points.
            largura_disponivel (float): Available width in points.

        Returns:
            float: Height occupied by the question in points.
        """
        pass

    @abstractmethod
    def calcular_altura_questao(self, questao_data: Dict[str, Any],
                               largura_disponivel: float) -> float:
        """
        Calculate the height needed to render a question.

        Args:
            questao_data (Dict[str, Any]): Question data (same structure as desenhar_questao).
            largura_disponivel (float): Available width in points.

        Returns:
            float: Calculated height needed in points.
        """
        pass

    def obter_estilos_paragraph(self) -> Dict[str, ParagraphStyle]:
        """
        Get a dictionary of ParagraphStyle objects for different text roles.

        This concrete method returns ReportLab ParagraphStyle objects that can be
        used for rendering text in the document. Styles are based on the configuration
        loaded from the YAML file.

        Returns:
            Dict[str, ParagraphStyle]: Dictionary with keys:
                - 'titulo': For question titles and headings
                - 'corpo': For main question text
                - 'opcoes': For answer options
                - 'instrucoes': For instructions text
                - 'rodape': For footer text

        Example:
            >>> base = SomeConcreteSubclass(config)
            >>> estilos = base.obter_estilos_paragraph()
            >>> titulo_style = estilos['titulo']
        """
        # Get sample styles as a base
        sample_styles = getSampleStyleSheet()

        # Extract font configuration from estilo_visual
        fonte_titulo = self.estilo_visual.get('fonte_titulo', 'Helvetica 12pt')
        fonte_corpo = self.estilo_visual.get('fonte_corpo', 'Times-Roman 10pt')

        # Parse font sizes (simple parsing for "Font Name Size" format)
        # e.g., "Helvetica / Arial Bold, 12pt-14pt" -> extract 12pt
        def extrair_tamanho_font(fonte_str: str) -> int:
            """Extract font size from font string."""
            if 'pt' in fonte_str:
                # Find all numbers followed by 'pt'
                import re
                matches = re.findall(r'(\d+(?:\.\d+)?)pt', fonte_str)
                if matches:
                    return int(float(matches[0]))
            return 12  # Default fallback

        tamanho_titulo = extrair_tamanho_font(fonte_titulo)
        tamanho_corpo = extrair_tamanho_font(fonte_corpo)

        # Get dominant colors or use defaults
        cores = self.estilo_visual.get('cores_dominantes', ['Preto', 'Branco'])
        cor_principal = colors.black  # Default to black
        if cores and cores[0].lower() != 'preto':
            # Could be extended to map color names to ReportLab colors
            cor_principal = colors.black

        # Define paragraph styles
        estilos = {
            'titulo': ParagraphStyle(
                name='BancaTitulo',
                fontName='Helvetica-Bold',
                fontSize=tamanho_titulo,
                textColor=cor_principal,
                spaceAfter=6,
                leading=tamanho_titulo * 1.2,
                alignment=0  # Left alignment (TA_LEFT)
            ),
            'corpo': ParagraphStyle(
                name='BancaCorpo',
                fontName='Times-Roman',
                fontSize=tamanho_corpo,
                textColor=cor_principal,
                spaceAfter=4,
                leading=tamanho_corpo * 1.4,
                alignment=4  # Justified alignment (TA_JUSTIFY)
            ),
            'opcoes': ParagraphStyle(
                name='BancaOpcoes',
                fontName='Helvetica',
                fontSize=tamanho_corpo - 1,
                textColor=cor_principal,
                spaceAfter=2,
                leading=tamanho_corpo * 1.2,
                alignment=0  # Left alignment
            ),
            'instrucoes': ParagraphStyle(
                name='BancaInstrucoes',
                fontName='Helvetica',
                fontSize=tamanho_corpo - 1,
                textColor=cor_principal,
                spaceAfter=4,
                leading=tamanho_corpo * 1.3,
                alignment=4,  # Justified alignment
                borderPadding=6,
                borderColor=cor_principal,
                borderWidth=1
            ),
            'rodape': ParagraphStyle(
                name='BancaRodape',
                fontName='Helvetica',
                fontSize=tamanho_corpo - 2,
                textColor=colors.grey,
                spaceAfter=0,
                leading=tamanho_corpo * 1.1,
                alignment=1  # Center alignment (TA_CENTER)
            )
        }

        return estilos

    def cm_para_pontos(self, centimetros: float) -> float:
        """
        Convert centimeters to ReportLab points (1 cm = 28.346... points).

        This helper method converts measurements from centimeters (commonly used
        for document margins and sizes) to ReportLab's native point unit.

        Args:
            centimetros (float): Length in centimeters.

        Returns:
            float: Length in ReportLab points.

        Raises:
            TypeError: If centimetros is not a number.
            ValueError: If centimetros is negative.

        Example:
            >>> base = SomeConcreteSubclass(config)
            >>> pontos = base.cm_para_pontos(2.0)  # 2 cm to points
            >>> assert pontos == 56.692913385826766
        """
        if not isinstance(centimetros, (int, float)):
            raise TypeError(f"centimetros must be a number, got {type(centimetros)}")

        if centimetros < 0:
            raise ValueError(f"centimetros must be non-negative, got {centimetros}")

        return centimetros * self.CM_TO_POINTS

    def carregar_config_yaml(self, caminho_arquivo: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.

        This helper method loads and parses a YAML configuration file.

        Args:
            caminho_arquivo (str): Path to the YAML configuration file.

        Returns:
            Dict[str, Any]: Parsed YAML configuration.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {caminho_arquivo}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {caminho_arquivo}: {e}")

    def obter_margens_cm(self) -> Dict[str, float]:
        """
        Get page margins from configuration in centimeters.

        Returns:
            Dict[str, float]: Margins with keys 'superior', 'inferior', 'esquerda', 'direita'.
        """
        margens_config = self.estilo_visual.get('margens', {})
        return {
            'superior': margens_config.get('superior_cm', 2.0),
            'inferior': margens_config.get('inferior_cm', 2.0),
            'esquerda': margens_config.get('esquerda_cm', 1.5),
            'direita': margens_config.get('direita_cm', 1.5)
        }

    def obter_margens_pontos(self) -> Dict[str, float]:
        """
        Get page margins from configuration in ReportLab points.

        Returns:
            Dict[str, float]: Margins in points with keys 'superior', 'inferior',
                            'esquerda', 'direita'.
        """
        margens_cm = self.obter_margens_cm()
        return {
            'superior': self.cm_para_pontos(margens_cm['superior']),
            'inferior': self.cm_para_pontos(margens_cm['inferior']),
            'esquerda': self.cm_para_pontos(margens_cm['esquerda']),
            'direita': self.cm_para_pontos(margens_cm['direita'])
        }
