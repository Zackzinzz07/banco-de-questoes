r"""Gera um simulado de SUAS. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_suas"""
from simulados import gerar_simulado

MATERIA = "SUAS"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
