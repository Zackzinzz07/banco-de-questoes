r"""Gera um simulado de Direito Constitucional. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_constitucional"""
from simulados import gerar_simulado

MATERIA = "Direito Constitucional"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
