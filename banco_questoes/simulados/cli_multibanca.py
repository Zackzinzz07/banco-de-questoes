"""CLI interface for multi-banca simulado generation using Click.

This module provides a command-line interface for generating exam documents
(simulados) in the style of various Brazilian exam boards (bancas).

Usage:
    python -m banco_questoes.simulados.cli_multibanca --banca cebraspe --quantidade 60 --nome simulado.pdf
    python cli_multibanca.py --banca iades --quantidade 120 --nome prova_iades.pdf
"""

import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulados.estilos import EstiloCebraspe


class GeradorSimuladoMultiBanca:
    """Generator for multi-banca exam documents (simulados).

    This class handles the generation of PDF exam documents tailored to
    specific exam boards (bancas). It orchestrates configuration loading,
    style instantiation, and PDF rendering.

    Attributes:
        BANCAS_DISPONIVEIS: Dict of available banca codes and their config files
        CONFIG_DIR: Directory containing banca configuration files
    """

    BANCAS_DISPONIVEIS = {
        'cebraspe': 'cebraspe.yaml',
        'iades': 'iades.yaml',
        'quadrix': 'quadrix.yaml',
        'fgv': 'fgv.yaml',
        'aocp': 'aocp.yaml',
    }

    def __init__(self):
        """Initialize the multi-banca generator."""
        self.config_dir = (Path(__file__).resolve().parent.parent /
                          'configuracoes_bancas')

    def carregar_configuracao(self, banca: str) -> dict:
        """Load configuration for a specific exam board.

        Args:
            banca: Code of the exam board (cebraspe, iades, quadrix, fgv, aocp)

        Returns:
            Dictionary containing the banca configuration from YAML

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the banca code is invalid
        """
        if banca not in self.BANCAS_DISPONIVEIS:
            raise ValueError(f"Banca '{banca}' not recognized. Available: {list(self.BANCAS_DISPONIVEIS.keys())}")

        config_file = self.config_dir / self.BANCAS_DISPONIVEIS[banca]

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def obter_classe_estilo(self, banca: str):
        """Get the style class for a specific exam board.

        Args:
            banca: Code of the exam board

        Returns:
            Style class for the banca (currently only EstiloCebraspe available)

        Raises:
            NotImplementedError: If the style class hasn't been implemented yet
        """
        estilos_implementados = {
            'cebraspe': EstiloCebraspe,
        }

        if banca not in estilos_implementados:
            raise NotImplementedError(
                f"Style for banca '{banca}' not yet implemented. "
                f"Available: {list(estilos_implementados.keys())}"
            )

        return estilos_implementados[banca]

    def gerar(self, banca: str, quantidade: int, nome_arquivo: Optional[str] = None) -> Path:
        """Generate a simulado in the style of a specific exam board.

        Args:
            banca: Code of the exam board (cebraspe, iades, quadrix, fgv, aocp)
            quantidade: Number of questions in the simulado
            nome_arquivo: Output filename (default: simulado_{banca}_{quantidade}q.pdf)

        Returns:
            Path to the generated PDF file

        Raises:
            ValueError: If banca or quantidade are invalid
            FileNotFoundError: If configuration files are missing
        """
        if quantidade <= 0:
            raise ValueError("Quantidade must be greater than 0")

        # Load configuration
        config = self.carregar_configuracao(banca)

        # Get style class and instantiate
        classe_estilo = self.obter_classe_estilo(banca)
        config_banca = config[banca]  # Extract banca-specific config
        estilo = classe_estilo(config_banca)

        # Determine output filename
        if nome_arquivo is None:
            nome_arquivo = f"simulado_{banca}_{quantidade}q.pdf"

        output_path = Path(nome_arquivo).resolve()

        # Create a simple PDF using ReportLab Canvas
        # This is a basic implementation showing the banca configuration
        self._criar_pdf_basico(output_path, estilo, banca, quantidade)

        return output_path

    def _criar_pdf_basico(self, output_path: Path, estilo, banca: str, quantidade: int):
        """Create a basic PDF document using the style.

        Args:
            output_path: Path where PDF will be saved
            estilo: Instance of a BaseBancaStyle subclass
            banca: Code of the exam board
            quantidade: Number of questions
        """
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create canvas
        c = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4

        # Draw using the style's methods
        # This demonstrates the integration with BaseBancaStyle

        # Draw header
        header_height = estilo.desenhar_cabecalho(c, 1, width, height)

        # Draw some sample questions
        y_position = height - header_height - 1 * cm

        for i in range(min(3, quantidade)):  # Draw up to 3 sample questions
            questao_data = {
                'numero': i + 1,
                'enunciado': f'Sample question {i + 1}: This is a test question from {banca.upper()} exam board.',
            }

            if i > 0:
                y_position -= 0.5 * cm

            question_height = estilo.desenhar_questao(
                c, questao_data, 1 * cm, y_position, width - 2 * cm
            )
            y_position -= question_height + 0.3 * cm

            # Add page break if needed
            if y_position < 2 * cm:
                # Draw footer on current page
                estilo.desenhar_rodape(c, c.getPageNumber(), width, height)
                c.showPage()
                y_position = height - 2 * cm
                header_height = estilo.desenhar_cabecalho(c, c.getPageNumber() + 1, width, height)
                y_position = height - header_height - 1 * cm

        # Draw footer on last page
        estilo.desenhar_rodape(c, c.getPageNumber(), width, height)

        # Save the PDF
        c.save()


@click.command()
@click.option(
    '--banca',
    type=click.Choice(['cebraspe', 'iades', 'quadrix', 'fgv', 'aocp'], case_sensitive=False),
    required=True,
    help='Exam board code (cebraspe, iades, quadrix, fgv, aocp)'
)
@click.option(
    '--quantidade',
    type=int,
    default=60,
    help='Number of questions in the simulado (default: 60)'
)
@click.option(
    '--nome',
    type=str,
    default=None,
    help='Output filename (default: simulado_{banca}_{quantidade}q.pdf)'
)
def gerar_simulado(banca: str, quantidade: int, nome: Optional[str]):
    """Generate a multi-banca exam document (simulado).

    Creates a PDF exam document in the style of a specified Brazilian exam board.

    Examples:

        \b
        # Cebraspe style with 30 questions
        python cli_multibanca.py --banca cebraspe --quantidade 30 --nome teste.pdf

        \b
        # IADES style with default 60 questions
        python cli_multibanca.py --banca iades

        \b
        # Quadrix style, custom filename
        python cli_multibanca.py --banca quadrix --quantidade 120 --nome prova_quadrix.pdf
    """
    try:
        # Normalize banca code to lowercase
        banca = banca.lower()

        # Display info message
        click.echo(f"Generating simulado for {banca.upper()}...", err=False)

        # Create generator and generate PDF
        gerador = GeradorSimuladoMultiBanca()
        output_path = gerador.gerar(banca, quantidade, nome)

        # Success message
        click.echo(f"[OK] Simulado generated successfully: {output_path}", err=False)
        click.echo(f"  Exam board: {banca.upper()}", err=False)
        click.echo(f"  Questions: {quantidade}", err=False)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)
    except NotImplementedError as e:
        click.echo(f"Not Yet Implemented: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    gerar_simulado()
