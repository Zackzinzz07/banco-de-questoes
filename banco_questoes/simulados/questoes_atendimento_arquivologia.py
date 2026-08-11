r"""Gera um simulado de Atendimento, Rotinas Administrativas e Arquivologia. Edite MATERIA/QUANTIDADE à vontade.
Rodar de banco_questoes\: ..\.venv\Scripts\python.exe -m simulados.questoes_atendimento_arquivologia"""
from simulados import gerar_simulado

MATERIA = "Atendimento, Rotinas Administrativas e Arquivologia"
QUANTIDADE = 20

gerar_simulado.gerar(MATERIA, QUANTIDADE)
