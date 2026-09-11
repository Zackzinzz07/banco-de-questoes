"""Testes unitários para a função de decisão e parsing do mapeador de editais.

Garante que a lógica de decisão seja rigorosa e não force correspondências fracas,
seguindo a regra de ouro do projeto ("erra para excluir, nunca inventa"), sem realizar
chamadas reais à rede ou à API da Claude.
"""

from unittest.mock import MagicMock

from scripts.mapear_conteudo_edital import (
    decidir_matches,
    extrair_json_resposta,
    julgar_topico_com_claude,
)


def test_decidir_matches_sucesso_direto():
    """Confiança acima do limiar e categoria presente na lista candidata."""
    categorias = ["Da Prisão e da Liberdade Provisória", "Inquérito Policial"]
    resposta_api = {
        "matches": ["Da Prisão e da Liberdade Provisória"],
        "confianca": 0.95,
        "justificativa": "Correspondência direta com medidas cautelares e prisão.",
    }

    resultado = decidir_matches(resposta_api, categorias, limiar_confianca=0.7)
    assert resultado == ["Da Prisão e da Liberdade Provisória"]


def test_decidir_matches_multiplos():
    """Múltiplas categorias presentes e válidas."""
    categorias = [
        "Inquérito Policial",
        "Procedimentos Alternativos de Investigação Criminal",
        "Das Provas",
    ]
    resposta_api = {
        "matches": [
            "Inquérito Policial",
            "Procedimentos Alternativos de Investigação Criminal",
        ],
        "confianca": 0.9,
    }

    resultado = decidir_matches(resposta_api, categorias, limiar_confianca=0.7)
    assert resultado == [
        "Inquérito Policial",
        "Procedimentos Alternativos de Investigação Criminal",
    ]


def test_decidir_matches_rejeita_abaixo_do_limiar():
    """Se a confiança for inferior ao limiar exigido, devolve vazio (buraco real)."""
    categorias = ["Teoria Geral do Delito", "Sanções penais"]
    resposta_api = {
        "matches": ["Teoria Geral do Delito"],
        "confianca": 0.55,  # Abaixo de 0.70
        "justificativa": "Semelhança tênue.",
    }

    resultado = decidir_matches(resposta_api, categorias, limiar_confianca=0.7)
    assert resultado == []


def test_decidir_matches_filtra_categoria_inexistente():
    """Descarta categorias inventadas/alucinadas pela LLM que não estão no banco."""
    categorias_reais = ["Direito Administrativo", "Atos administrativos"]
    resposta_api = {
        "matches": ["Atos administrativos", "Categoria Que Não Existe No Banco"],
        "confianca": 0.95,
    }

    resultado = decidir_matches(resposta_api, categorias_reais, limiar_confianca=0.7)
    assert resultado == ["Atos administrativos"]


def test_decidir_matches_resposta_vazia():
    """Quando o modelo conclui que não há correspondência real."""
    categorias = ["Princípios Fundamentais da República", "Poder Legislativo"]
    resposta_api = {
        "matches": [],
        "confianca": 0.0,
        "justificativa": "Nenhuma correspondência.",
    }

    resultado = decidir_matches(resposta_api, categorias, limiar_confianca=0.7)
    assert resultado == []


def test_decidir_matches_dados_malformados():
    """Trata graciosamente tipos inválidos na resposta da API."""
    assert decidir_matches({}, ["Atos"]) == []
    assert decidir_matches(None, ["Atos"]) == []  # type: ignore
    assert decidir_matches({"matches": "não é lista", "confianca": 0.9}, ["Atos"]) == []
    assert decidir_matches({"matches": ["Atos"], "confianca": "inválido"}, ["Atos"]) == []


def test_extrair_json_bloco_markdown():
    """Extrai JSON envelopado em bloco markdown com ou sem tag 'json'."""
    texto = """Aqui está a análise:
```json
{
  "matches": ["Teoria da Constituição"],
  "confianca": 0.92,
  "justificativa": "Tema idêntico."
}
```
Espero ter ajudado."""

    dados = extrair_json_resposta(texto)
    assert dados["matches"] == ["Teoria da Constituição"]
    assert dados["confianca"] == 0.92


def test_extrair_json_texto_puro():
    """Extrai JSON inserido no meio de texto sem delimitadores markdown."""
    texto = 'Resultado: {"matches": ["Controle da administração pública"], "confianca": 0.85}'
    dados = extrair_json_resposta(texto)
    assert dados["matches"] == ["Controle da administração pública"]
    assert dados["confianca"] == 0.85


def test_extrair_json_invalido():
    """Retorna dicionário vazio se o texto não contiver JSON válido."""
    assert extrair_json_resposta("Texto qualquer sem chaves nem json.") == {}
    assert extrair_json_resposta("") == {}


def test_julgar_topico_sem_categorias_disponiveis():
    """Se a lista de categorias for vazia, não chama a API e retorna sem match."""
    client_mock = MagicMock()
    res = julgar_topico_com_claude(
        client=client_mock,
        topico="Criminologia Geral",
        categorias_disponiveis=[],
        materia_edital="Criminologia",
    )
    assert res["matches"] == []
    assert res["confianca"] == 0.0
    client_mock.messages.create.assert_not_called()


def test_julgar_topico_simulando_cliente_anthropic():
    """Simula o retorno de client.messages.create e confere o pipeline de julgamento."""
    client_mock = MagicMock()
    conteudo_mock = MagicMock()
    conteudo_mock.text = '{"matches": ["Ortografia"], "confianca": 0.98, "justificativa": "Match"}'

    mensagem_mock = MagicMock()
    mensagem_mock.content = [conteudo_mock]
    client_mock.messages.create.return_value = mensagem_mock

    categorias = ["Ortografia", "Pontuação", "Sintaxe"]
    res = julgar_topico_com_claude(
        client=client_mock,
        topico="Ortografia oficial.",
        categorias_disponiveis=categorias,
        materia_edital="Língua Portuguesa",
    )

    decisao = decidir_matches(res, categorias, limiar_confianca=0.7)
    assert decisao == ["Ortografia"]
    client_mock.messages.create.assert_called_once()
