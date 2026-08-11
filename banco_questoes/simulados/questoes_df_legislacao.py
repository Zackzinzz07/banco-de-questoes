r"""Gera um simulado de Conhecimentos do DF e Legislação. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_df_legislacao"""
from simulados import gerar_simulado

MATERIA = "Conhecimentos do DF e Legislação"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
