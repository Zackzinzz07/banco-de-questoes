"""CLI interface para geração de simulados multi-banca usando Click.

Módulo que fornece interface de linha de comando para gerar documentos de prova
(simulados) no estilo de várias bancas examinadoras brasileiras.

Uso:
    # Simulado básico
    python -m banco_questoes.simulados.cli_multibanca \
      --banca cebraspe \
      --quantidade 60 \
      --nome simulado.pdf

    # Com filtro de banca/órgão específicos (imersivo)
    python -m banco_questoes.simulados.cli_multibanca \
      --banca quadrix \
      --quantidade 50 \
      --banca-concurso "Instituto Quadrix" \
      --orgao "SEDES/DF"
"""

import sys
from pathlib import Path
from typing import Optional

import click

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulados.gerador_multibanca import GeradorSimuladoMultiBanca


@click.command()
@click.option(
    '--banca',
    type=click.Choice(['cebraspe', 'iades', 'quadrix', 'fgv', 'aocp'], case_sensitive=False),
    required=True,
    help='Código da banca (cebraspe, iades, quadrix, fgv, aocp)'
)
@click.option(
    '--quantidade',
    type=int,
    default=60,
    help='Número de questões no simulado (padrão: 60)'
)
@click.option(
    '--nome',
    type=str,
    default=None,
    help='Nome do arquivo de saída (padrão: simulado_{banca}_{quantidade}q.pdf)'
)
@click.option(
    '--banca-concurso',
    type=str,
    default=None,
    help='Nome da banca examinadora para filtro (ex: "Instituto Quadrix"). '
         'Se fornecido, prioriza questões dessa banca.'
)
@click.option(
    '--orgao',
    type=str,
    default=None,
    help='Órgão/concurso para filtro (ex: "SEDES/DF"). '
         'Se fornecido, prioriza questões desse órgão.'
)
def gerar_simulado(
    banca: str,
    quantidade: int,
    nome: Optional[str],
    banca_concurso: Optional[str],
    orgao: Optional[str]
):
    """Gera um documento de prova multi-banca (simulado).

    Cria um PDF de prova no estilo de uma banca examinadora brasileira específica.

    Exemplos:

        \b
        # Cebraspe com 30 questões
        python -m banco_questoes.simulados.cli_multibanca --banca cebraspe --quantidade 30

        \b
        # Quadrix com filtro de banca/órgão específicos
        python -m banco_questoes.simulados.cli_multibanca \\
          --banca quadrix \\
          --quantidade 50 \\
          --banca-concurso "Instituto Quadrix" \\
          --orgao "SEDES/DF"
    """
    try:
        # Normaliza código da banca
        banca = banca.lower()

        # Mensagem inicial
        click.echo(f"Gerando simulado para {banca.upper()}...", err=False)
        if banca_concurso:
            click.echo(f"  Filtro de banca: {banca_concurso}", err=False)
        if orgao:
            click.echo(f"  Filtro de órgão: {orgao}", err=False)

        # Cria gerador e gera PDF
        gerador = GeradorSimuladoMultiBanca(
            banca,
            banca_concurso=banca_concurso,
            orgao=orgao
        )
        output_path = gerador.gerar(quantidade, nome or f"Simulado_{banca.capitalize()}_{quantidade}q")

        # Mensagem de sucesso
        click.echo(f"[OK] Simulado gerado com sucesso: {output_path}", err=False)
        click.echo(f"  Banca: {banca.upper()}", err=False)
        click.echo(f"  Questões: {quantidade}", err=False)

    except ValueError as e:
        click.echo(f"Erro: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"Erro de Configuração: {e}", err=True)
        sys.exit(1)
    except NotImplementedError as e:
        click.echo(f"Ainda não implementado: {e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"Erro de Execução: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Erro inesperado: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    gerar_simulado()
