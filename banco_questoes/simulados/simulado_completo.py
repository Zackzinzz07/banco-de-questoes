r"""Gera o Simulado Geral. Rodar de banco_questoes\:
..\.venv\Scripts\python.exe -m simulados.simulado_completo 60"""
import sys

from simulados import gerar_simulado

quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 60
gerar_simulado.gerar_completo(quantidade)
