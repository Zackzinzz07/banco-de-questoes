"""Mapeador unificado: Matéria → Categoria → Tema.

Funciona para TODOS os concursos (PCI, QConcursos, etc).
"""

import yaml
from pathlib import Path

# Carregar mapeamento
MAPEAMENTO_PATH = Path(__file__).resolve().parent / "mapeamento_conteudos.yaml"

try:
    with open(MAPEAMENTO_PATH) as f:
        MAPEAMENTO = yaml.safe_load(f)
except Exception as e:
    print(f"Erro ao carregar mapeamento_conteudos.yaml: {e}")
    MAPEAMENTO = {}


def obter_categorias(materia):
    """Retorna lista de categorias para uma matéria.

    Ex: obter_categorias("Português") → ["ortografia", "morfologia", "sintaxe"]
    """
    if materia not in MAPEAMENTO:
        return []

    return list(MAPEAMENTO[materia].keys())


def obter_temas(materia, categoria):
    """Retorna lista de temas para uma categoria dentro de uma matéria.

    Ex: obter_temas("Português", "ortografia") → ["acentuação", "pontuação", "crase"]
    """
    if materia not in MAPEAMENTO:
        return []

    if categoria not in MAPEAMENTO[materia]:
        return []

    return MAPEAMENTO[materia][categoria]


def sugerir_categoria(materia, enunciado_snippet):
    """Tenta adivinhar categoria baseado em palavras-chave no enunciado.

    Retorna: (categoria, confiança 0.0-1.0)
    Simples heurística baseada em keywords.
    """

    if materia not in MAPEAMENTO:
        return None, 0.0

    enunciado = enunciado_snippet.lower()

    categorias = MAPEAMENTO[materia]
    matches = {}

    # Mapeamento de keywords → categoria
    keywords_map = {
        "Português": {
            "ortografia": ["acento", "acentua", "crase", "pontuação", "virgula"],
            "morfologia": ["verbo", "adjetivo", "substantivo", "pronome", "preposição"],
            "sintaxe": ["oração", "período", "colocação", "termo", "predicado"],
        },
        "Matemática": {
            "aritmética": ["operação", "fração", "percentual", "decimal", "divisão"],
            "álgebra": ["equação", "função", "logaritmo", "potência", "raiz"],
            "geometria": ["triângulo", "quadrado", "círculo", "ângulo", "trigonometria"],
            "estatística": ["média", "moda", "mediana", "probabilidade", "distribuição"],
        },
        "Direito Administrativo": {
            "atos-administrativos": ["ato administrativo", "nulidade", "anulação", "rescisão"],
            "poder-discricionário": ["discricionário", "vinculado", "margem", "apreciação"],
            "servidores-públicos": ["servidor", "funcionário", "agente público", "cargo"],
            "licitação": ["licitação", "concorrência", "pregão", "contrato administrativo"],
            "bens-públicos": ["bem público", "domínio", "patrimônio público"],
        },
    }

    if materia in keywords_map:
        for cat, keywords in keywords_map[materia].items():
            count = sum(1 for kw in keywords if kw in enunciado)
            if count > 0:
                matches[cat] = count / len(keywords)

    if matches:
        best_cat = max(matches, key=matches.get)
        return best_cat, matches[best_cat]

    # Fallback: primeira categoria da matéria
    if categorias:
        return list(categorias.keys())[0], 0.3

    return None, 0.0


def normalizar_categoria(texto):
    """Normaliza nome de categoria para slug.

    Ex: "Atos Administrativos" → "atos-administrativos"
    """
    return texto.lower().replace(" ", "-").replace("_", "-")


# Teste
if __name__ == "__main__":
    print("Mapeamento carregado:", bool(MAPEAMENTO))
    print("Matérias:", list(MAPEAMENTO.keys())[:3] if MAPEAMENTO else "VAZIO")

    mat = "Portugu~es"  # Nota: sem acentos para evitar problemas de encoding
    print(f"\nCategorias de {mat}:", obter_categorias(mat))
    print(f"Temas de {mat}/ortografia:", obter_temas(mat, "ortografia"))

    # Testar sugestão
    enunciado = "Qual o uso correto de acentuação na palavra XXX?"
    cat, conf = sugerir_categoria("Português", enunciado)
    print(f"Sugestão: {cat} (confiança: {conf:.1%})")
