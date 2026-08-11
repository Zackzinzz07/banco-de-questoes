r"""Gera um simulado de Língua Portuguesa. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_portugues"""
from simulados import gerar_simulado

MATERIA = "Língua Portuguesa"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
