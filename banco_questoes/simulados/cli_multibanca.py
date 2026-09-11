"""CLI interface para geração de simulados multi-banca e por edital.

Atende às regras do CLAUDE.md: orquestrador com menos de 60 linhas e
gestão segura de conexão via try/finally.
"""

import sys

import click

import db
import edital_loader
from simulados import por_edital
from simulados.gerador_multibanca import GeradorSimuladoMultiBanca


@click.command()
@click.option("--banca", "--estilo", "banca", default="cebraspe", help="Estilo visual da banca")
@click.option("--concurso", default=None, help="Slug do edital (ex: pmdf, prf, inss)")
@click.option("--cargo", default=None, help="Nome do cargo no edital")
@click.option("--quantidade", type=int, default=60, help="Número de questões")
@click.option("--nome", default=None, help="Nome do arquivo de saída")
def main(banca: str, concurso: str | None, cargo: str | None, quantidade: int, nome: str | None):
    """Gera simulados por edital ou por banca no estilo visual escolhido."""
    banca = banca.lower()
    con = db.conectar()
    try:
        questoes = None
        if concurso:
            cargos = edital_loader.listar_cargos(concurso)
            if not cargos:
                click.echo(f"Erro: concurso '{concurso}' não encontrado.", err=True)
                sys.exit(1)
            cargo = cargo or cargos[0]
            edital = edital_loader.carregar_edital(concurso) or {}
            pesos = edital_loader.obter_pesos(concurso, cargo)
            click.echo(f"Simulado {concurso.upper()} ({cargo}) | Estilo: {banca.upper()}")
            sim = por_edital.montar(
                con, pesos, quantidade, formato=edital.get("formato"), banca=edital.get("banca")
            )
            for mat, falta in sim.lacunas.items():
                click.echo(f"  [LACUNA] {mat}: faltam {falta} questões no acervo", err=True)
            questoes = sim.questoes
            nome = nome or f"simulado_{concurso}_{banca}_{quantidade}q.pdf"

        gerador = GeradorSimuladoMultiBanca(banca, con=con, concurso=concurso, cargo=cargo)
        alvo = nome or f"simulado_{banca}_{quantidade}q.pdf"
        saida = gerador.gerar(quantidade, alvo, questoes=questoes)
        click.echo(f"[OK] Simulado gerado com sucesso: {saida}")
    except Exception as e:
        click.echo(f"Erro: {e}", err=True)
        sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
