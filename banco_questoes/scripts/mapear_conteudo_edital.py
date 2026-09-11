"""Mapeamento semântico de tópicos de edital contra categorias do acervo PostgreSQL.

Cruza o conteúdo programático oficial de um cargo (arquivo YAML) contra os valores
distintos da coluna `categoria` no banco de dados, utilizando a API da Claude para
fazer o julgamento semântico criterioso.

Regra de ouro (CLAUDE.md): "Erra para excluir, nunca inventa". Se a correspondência
for fraca, genérica ou duvidosa, classifica como "SEM CORRESPONDÊNCIA" (lista vazia).

Arquitetura em camadas:
- Persistência / I/O: leitura de banco com injeção de dependência e leitura de YAML.
- Avaliação Semântica: chamada isolada à API da Claude (Anthropic).
- Decisão e Parsing: funções puras sem I/O, validadas por testes unitários.
- Orquestrador CLI: ponto de entrada para execução via terminal.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import db  # noqa: E402
import taxonomia  # noqa: E402

load_dotenv()

EDITAIS_DIR = ROOT_DIR / "configuracoes_editais"

PROMPT_SISTEMA_JULGAMENTO = """Você é um especialista em taxonomia de concursos públicos.
Avalie se um TÓPICO de edital corresponde a CATEGORIAS cadastradas no acervo do banco.

REGRA DE OURO (MANDATÓRIA DO PROJETO):
- "Erra para EXCLUIR, NUNCA inventa".
- Só considere MATCH se a categoria representar com precisão direta o tema do tópico.
- Se a categoria for meramente uma disciplina guarda-chuva, NÃO marque match.
- Ramos distintos do direito (ex.: penal comum vs penal militar) JAMAIS casam.
- Se a relação for tangencial, fraca ou duvidosa, marque lista vazia e confiança 0.0.

Você DEVE responder ESTRITAMENTE em formato JSON com o seguinte schema:
{
  "matches": ["Categoria Exata da Lista Candidata 1", "..."],
  "confianca": 0.95,
  "justificativa": "breve explicação objetiva"
}
Se não houver correspondência com segurança:
{
  "matches": [],
  "confianca": 0.0,
  "justificativa": "Nenhuma categoria candidata cobre o tópico com precisão."
}
"""


# ==============================================================================
# CAMADA 1: Funções Puras de Decisão e Parsing (Sem I/O, 100% Testáveis)
# ==============================================================================


def extrair_json_resposta(texto_resposta: str) -> dict[str, Any]:
    """Extrai e faz parsing do JSON contido na resposta em texto da API.

    Trata casos onde o modelo envolve o JSON em blocos markdown ```json ... ```.
    """
    if not texto_resposta:
        return {}

    texto_limpo = texto_resposta.strip()
    match_bloco = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto_limpo, re.DOTALL)
    if match_bloco:
        texto_limpo = match_bloco.group(1).strip()

    try:
        dados = json.loads(texto_limpo)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        inicio = texto_resposta.find("{")
        fim = texto_resposta.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            try:
                dados = json.loads(texto_resposta[inicio : fim + 1])
                return dados if isinstance(dados, dict) else {}
            except Exception:
                pass
        return {}


def decidir_matches(
    resposta_api: dict[str, Any],
    categorias_disponiveis: list[str],
    limiar_confianca: float = 0.7,
) -> list[str]:
    """Aplica os guardrails e limiar de confiança sobre a resposta da LLM.

    Função pura:
    1. Rejeita se a confiança informada for inferior ao limiar.
    2. Garante que apenas categorias que realmente existam na lista candidata
       sejam retornadas (evita alucinação de novas categorias).
    3. Descarta correspondências ambíguas ou ausentes.
    """
    if not isinstance(resposta_api, dict):
        return []

    try:
        confianca = float(resposta_api.get("confianca", 0.0))
    except (ValueError, TypeError):
        return []

    if confianca < limiar_confianca:
        return []

    candidatos = resposta_api.get("matches", [])
    if not isinstance(candidatos, list):
        return []

    conjunto_validas = set(categorias_disponiveis)
    matches_confirmados = [
        c for c in candidatos if isinstance(c, str) and c in conjunto_validas
    ]

    return matches_confirmados


# ==============================================================================
# CAMADA 2: Chamada à API da Claude (Anthropic)
# ==============================================================================


def julgar_topico_com_claude(
    client: Any,
    topico: str,
    categorias_disponiveis: list[str],
    materia_edital: str,
    modelo: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Envia um tópico e a lista de categorias disponíveis para julgamento na Claude API."""
    if not categorias_disponiveis:
        return {
            "matches": [],
            "confianca": 0.0,
            "justificativa": "Sem categorias disponíveis.",
        }

    prompt_usuario = (
        f"MATÉRIA DO EDITAL: {materia_edital}\n"
        f"TÓPICO A CLASSIFICAR:\n\"{topico}\"\n\n"
        f"CATEGORIAS DISPONÍVEIS NO BANCO:\n"
        + "\n".join(f"- {cat}" for cat in sorted(categorias_disponiveis))
        + "\n\nIdentifique quais categorias acima (se houver) cobrem este tópico."
    )

    try:
        mensagem = client.messages.create(
            model=modelo,
            max_tokens=400,
            temperature=0.0,
            system=PROMPT_SISTEMA_JULGAMENTO,
            messages=[{"role": "user", "content": prompt_usuario}],
        )
        texto_corpo = mensagem.content[0].text if mensagem.content else ""
        return extrair_json_resposta(texto_corpo)
    except Exception as e:
        return {"matches": [], "confianca": 0.0, "erro": str(e)}


# ==============================================================================
# CAMADA 3: Persistência e Leitura de Arquivos / Banco de Dados
# ==============================================================================


def localizar_arquivo_conteudo(
    edital_slug: str, cargo: str, base_dir: Path = EDITAIS_DIR
) -> Path:
    """Localiza o arquivo de conteúdo programático para o concurso e cargo informados."""
    cargo_normalizado = taxonomia.normalizar(cargo).replace(" ", "_")
    candidato_1 = base_dir / f"{edital_slug}_{cargo_normalizado}_conteudo_programatico.yaml"
    if candidato_1.exists():
        return candidato_1

    for palavra in cargo_normalizado.split("_"):
        if len(palavra) >= 4:
            candidato_palavra = (
                base_dir / f"{edital_slug}_{palavra}_conteudo_programatico.yaml"
            )
            if candidato_palavra.exists():
                return candidato_palavra

    for arquivo in base_dir.glob(f"{edital_slug}_*_conteudo_programatico.yaml"):
        return arquivo

    raise FileNotFoundError(
        f"Não foi encontrado arquivo de conteúdo programático para edital '{edital_slug}' "
        f"e cargo '{cargo}' em {base_dir}"
    )


def carregar_conteudo_programatico(caminho_yaml: Path) -> dict[str, Any]:
    """Carrega o arquivo YAML com os tópicos do edital."""
    with open(caminho_yaml, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    if not dados or "materias" not in dados:
        raise ValueError(f"Estrutura inválida em {caminho_yaml}: chave 'materias' obrigatória.")
    return dados


def obter_categorias_banco(conn: Any, materias_banco: list[str]) -> dict[str, list[str]]:
    """Consulta categorias distintas no PostgreSQL para as matérias resolvidas."""
    resultado: dict[str, list[str]] = {}
    with conn.cursor() as cur:
        for materia in materias_banco:
            cur.execute(
                "SELECT DISTINCT categoria FROM questoes "
                "WHERE materia = %s AND categoria IS NOT NULL ORDER BY categoria",
                (materia,),
            )
            rows = cur.fetchall()
            cats = []
            for r in rows:
                val = r["categoria"] if isinstance(r, dict) else r[0]
                if val:
                    cats.append(val)
            resultado[materia] = cats
    return resultado


def obter_materias_disponiveis(conn: Any) -> list[str]:
    """Lista todas as matérias distintas existentes no banco."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT materia FROM questoes WHERE materia IS NOT NULL")
        rows = cur.fetchall()
        return [r["materia"] if isinstance(r, dict) else r[0] for r in rows]


# ==============================================================================
# CAMADA 4: Orquestração do Mapeamento e CLI
# ==============================================================================


def mapear_edital(
    conn: Any,
    client: Any,
    conteudo_yaml: Path,
    limiar_confianca: float = 0.7,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """Orquestra o mapeamento de todas as matérias do conteúdo programático."""
    dados_edital = carregar_conteudo_programatico(conteudo_yaml)
    materias_edital = dados_edital.get("materias", {})
    materias_banco_disponiveis = obter_materias_disponiveis(conn)

    resultado_mapeamento: dict[str, Any] = {
        "cargo": dados_edital.get("cargo", ""),
        "fonte_edital": dados_edital.get("fonte_edital", ""),
        "materias": {},
    }

    for nome_materia, info_materia in materias_edital.items():
        topicos = info_materia.get("conteudos", [])
        materias_banco = taxonomia.resolver(nome_materia, materias_banco_disponiveis)

        if not materias_banco:
            if verbose:
                print(f"\n[!] Matéria '{nome_materia}': SEM CORRESPONDÊNCIA no acervo.")
            resultado_mapeamento["materias"][nome_materia] = {
                "materias_banco": [],
                "topicos": [
                    {
                        "topico_edital": t,
                        "categorias_banco": [],
                        "status": "SEM CORRESPONDENCIA (matéria ausente no acervo)",
                    }
                    for t in topicos
                ],
            }
            continue

        cats_por_materia = obter_categorias_banco(conn, materias_banco)
        todas_cats: list[str] = []
        for cats in cats_por_materia.values():
            todas_cats.extend(cats)
        todas_cats = sorted(list(set(todas_cats)))

        if verbose:
            print(
                f"\n[*] Matéria '{nome_materia}' -> Banco: {materias_banco} "
                f"({len(todas_cats)} categorias, {len(topicos)} tópicos)"
            )

        topicos_processados = []
        for topico in topicos:
            if dry_run or not todas_cats:
                matches: list[str] = []
                status = (
                    "SEM CORRESPONDENCIA (sem categorias disponíveis)"
                    if not todas_cats
                    else "DRY-RUN"
                )
            else:
                resp_api = julgar_topico_com_claude(
                    client=client,
                    topico=topico,
                    categorias_disponiveis=todas_cats,
                    materia_edital=nome_materia,
                )
                matches = decidir_matches(
                    resp_api, todas_cats, limiar_confianca=limiar_confianca
                )
                status = "MATCH" if matches else "SEM CORRESPONDENCIA (buraco real)"

            if verbose:
                simbolo = "✓" if matches else "✗"
                print(f"  [{simbolo}] {topico[:70]}... -> {matches or 'BURACO REAL'}")

            topicos_processados.append(
                {
                    "topico_edital": topico,
                    "categorias_banco": matches,
                    "status": status,
                }
            )

        resultado_mapeamento["materias"][nome_materia] = {
            "materias_banco": materias_banco,
            "topicos": topicos_processados,
        }

    return resultado_mapeamento


def main() -> None:
    """Ponto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="Mapeia semânticamente tópicos de edital contra categorias via Claude."
    )
    parser.add_argument("--edital", required=True, help="Slug do edital (ex: pmdf, sedes_df)")
    parser.add_argument(
        "--cargo", required=True, help="Nome do cargo (ex: 'Soldado Policial Militar')"
    )
    parser.add_argument(
        "--conteudo-yaml", default=None, help="Caminho opcional do arquivo de conteúdo"
    )
    parser.add_argument("--saida", default=None, help="Arquivo de saída (.yaml ou .json)")
    parser.add_argument(
        "--limiar", type=float, default=0.7, help="Limiar de confiança (padrão: 0.7)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Executa sem chamar a API da Claude"
    )

    args = parser.parse_args()

    if args.conteudo_yaml:
        caminho_conteudo = Path(args.conteudo_yaml)
    else:
        caminho_conteudo = localizar_arquivo_conteudo(args.edital, args.cargo)

    client = None
    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print(
                "ERRO: Variável ANTHROPIC_API_KEY não encontrada no ambiente ou .env.\n"
                "Para testar a leitura do banco e edital sem gastar API, use a flag --dry-run.",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            print(
                "ERRO: Pacote 'anthropic' não instalado. Execute: pip install anthropic",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Iniciando mapeamento para edital: {args.edital} | cargo: {args.cargo}")
    print(f"Arquivo de conteúdo: {caminho_conteudo}")

    conn = db.conectar()
    try:
        resultado = mapear_edital(
            conn=conn,
            client=client,
            conteudo_yaml=caminho_conteudo,
            limiar_confianca=args.limiar,
            dry_run=args.dry_run,
        )
    finally:
        conn.close()

    caminho_saida = args.saida
    if not caminho_saida:
        cargo_slug = taxonomia.normalizar(args.cargo).replace(" ", "_")
        caminho_saida = EDITAIS_DIR / f"{args.edital}_{cargo_slug}_mapeamento_categorias.yaml"
    else:
        caminho_saida = Path(caminho_saida)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    if str(caminho_saida).endswith(".json"):
        with open(caminho_saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
    else:
        with open(caminho_saida, "w", encoding="utf-8") as f:
            yaml.dump(resultado, f, allow_unicode=True, sort_keys=False)

    print(f"\n[OK] Mapeamento concluído com sucesso! Salvo em: {caminho_saida}")


if __name__ == "__main__":
    main()
