r"""Gera um simulado de Recursos Materiais, Patrimônio e Compras. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_recursos_materiais"""
from simulados import gerar_simulado

MATERIA = "Recursos Materiais, Patrimônio e Compras"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
