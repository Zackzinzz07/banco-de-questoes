r"""Gera um simulado de Programas e Benefícios do DF. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_programas_df"""
from simulados import gerar_simulado

MATERIA = "Programas e Benefícios do DF"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
