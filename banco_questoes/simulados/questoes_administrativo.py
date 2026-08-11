r"""Gera um simulado de Direito Administrativo. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_administrativo"""
from simulados import gerar_simulado

MATERIA = "Direito Administrativo"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
