"""Importador em Lote: Transfere todos os cadernos Cebraspe arquivados no SSD/HD
(`provas_pdf/cebraspe/<slug>/itens.json`) para a tabela `questoes` no PostgreSQL.

Uso:
    python -m scripts.importar_lote_cebraspe
    python -m scripts.importar_lote_cebraspe --pasta /mnt/ssd/banco_questoes/provas_pdf/cebraspe

Mapeia automaticamente certames conhecidos para seus editais (PRF, DPDF, etc.)
e classifica matérias clássicas de certames gerais (DEPEN, ABIN, CNJ, etc.)
usando heurística pedagógica estrita ("erra para excluir").
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import db
    import edital_loader
    from scripts.importar_cebraspe import importar as importar_edital
except ImportError:
    from banco_questoes import db, edital_loader
    from banco_questoes.scripts.importar_cebraspe import importar as importar_edital

PASTA_PADRAO = Path(__file__).resolve().parent.parent / "provas_pdf" / "cebraspe"

_GABARITO = {"CERTO": "C", "ERRADO": "E"}

# Mapeamento de slugs do Cebraspe para editais conhecidos no projeto
_MAPEAMENTO_EDITAIS: dict[str, tuple[str, str | None]] = {
    "PRF_21": ("prf", "Policial Rodoviário Federal"),
    "PRF_19": ("prf", "Policial Rodoviário Federal"),
    "BCB_24": ("bacen", None),
    "INSS_22": ("inss", None),
    "INSS_16": ("inss", None),
}

# Palavras-chave para classificação temática segura de itens gerais
_PALAVRAS_CHAVE: dict[str, tuple[str, ...]] = {
    "Língua Portuguesa": (
        "sentido do texto",
        "ideias do texto",
        "segundo o texto",
        "de acordo com o texto",
        "conclui se do texto",
        "reescrita do trecho",
        "reescrita da oração",
        "correção gramatical",
        "sintaticamente",
        "coesão e coerência",
        "sinal indicativo de crase",
        "concordância verbal",
        "concordância nominal",
        "regência verbal",
        "regência nominal",
        "acentuação gráfica",
        "vocábulo",
        "morfossintaxe",
    ),
    "Raciocínio Lógico e Matemático": (
        "proposição",
        "tabela-verdade",
        "tabela verdade",
        "silogismo",
        "tautologia",
        "equivalência lógica",
        "negação da proposição",
        "probabilidade de que",
        "anagramas",
        "número de maneiras distintas",
    ),
    "Noções de Informática Operacional": (
        "sistema operacional linux",
        "sistema operacional windows",
        "navegador google chrome",
        "navegador edge",
        "correio eletrônico",
        "firewall",
        "malware",
        "ransomware",
        "phishing",
        "computação em nuvem",
        "backup incremental",
        "protocolo https",
        "protocolo tcp ip",
    ),
    "Noções de Direito Constitucional": (
        "constituição federal de 1988",
        "constituição da república",
        "direitos e garantias fundamentais",
        "direitos sociais",
        "remédios constitucionais",
        "supremo tribunal federal",
        "poder judiciário",
        "poder legislativo",
        "poder executivo",
        "estado de sítio",
        "estado de defesa",
    ),
    "Noções de Direito Administrativo": (
        "administração pública direta e indireta",
        "princípios da administração pública",
        "ato administrativo",
        "poder de polícia",
        "poder hierárquico",
        "lei n. 8.666",
        "lei n. 14.133",
        "licitação",
        "improbidade administrativa",
        "responsabilidade civil do estado",
        "servidor público",
    ),
    "Direito Penal e Processual Penal": (
        "código penal",
        "código de processo penal",
        "inquérito policial",
        "ação penal pública",
        "prisão em flagrante",
        "prisão preventiva",
        "crime doloso",
        "crime culposo",
        "legítima defesa",
        "estado de necessidade",
        "imputabilidade penal",
        "tipicidade da conduta",
        "extinção da punibilidade",
    ),
    "Direitos Humanos e Criminologia": (
        "declaração universal dos direitos humanos",
        "pacto de são josé da costa rica",
        "convenção americana sobre direitos humanos",
        "tratados internacionais de direitos humanos",
        "criminologia",
        "escola clássica",
        "escola positiva",
        "vitorimização primária",
        "vitorimização secundária",
    ),
}


def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def classificar_materia(enunciado: str) -> str | None:
    """Classifica a matéria do item por termos canônicos exclusivos."""
    texto = normalizar_texto(enunciado)
    for materia, termos in _PALAVRAS_CHAVE.items():
        for termo in termos:
            if termo in texto:
                return materia
    return None


def importar_pasta(con, caminho_pasta: Path) -> dict[str, int]:
    """Varre todas as subpastas procurando itens.json e persiste no banco."""
    pastas_concurso = [p for p in caminho_pasta.iterdir() if p.is_dir() and (p / "itens.json").exists()]
    if not pastas_concurso:
        print(f"Nenhum itens.json encontrado em {caminho_pasta}")
        return {"total_pastas": 0, "salvas": 0, "duplicadas": 0}

    print(f"📦 Encontrados {len(pastas_concurso)} concursos com itens.json para importar...\n")

    total_salvas = 0
    total_duplicadas = 0
    total_sem_materia = 0

    for idx, pasta in enumerate(sorted(pastas_concurso, key=lambda p: p.name), 1):
        slug = pasta.name
        arquivo_json = pasta / "itens.json"
        try:
            itens = json.loads(arquivo_json.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[{idx}/{len(pastas_concurso)}] ❌ {slug}: Erro ao ler JSON ({e})")
            continue

        if not itens:
            continue

        # 1. Tentar mapeamento direto com edital estruturado
        if slug in _MAPEAMENTO_EDITAIS:
            slug_edital, cargo = _MAPEAMENTO_EDITAIS[slug]
            try:
                res = importar_edital(con, itens, slug_edital, cargo)
                total_salvas += res["salvas"]
                total_duplicadas += res["duplicadas"]
                print(f"[{idx}/{len(pastas_concurso)}] 🎯 {slug} (via edital {slug_edital}): +{res['salvas']} salvas ({res['duplicadas']} duplicadas)")
                continue
            except Exception as err:
                print(f"[{idx}/{len(pastas_concurso)}] ⚠️ {slug}: Falha na importação por edital ({err}), usando classificação temática...")

        # 2. Classificação temática direta para os demais certames
        salvas_slug = 0
        dup_slug = 0
        for item in itens:
            enunciado = item.get("enunciado", "")
            materia = classificar_materia(enunciado)
            if not materia:
                total_sem_materia += 1
                continue

            gab = _GABARITO.get((item.get("gabarito") or "").upper())
            q = {
                "id_qc": f"cebraspe_{item.get('concurso', slug)}_{item.get('arquivo', 'pdf')}_{item.get('numero')}",
                "enunciado": enunciado,
                "alternativas": {"C": "Certo", "E": "Errado"},
                "gabarito": gab,
                "comentario": item.get("justificativa") or None,
                "materia": materia,
                "banca": "Cebraspe",
                "orgao": item.get("concurso", slug),
                "ano": None,
                "fonte": "cebraspe",
                "formato": "certo_errado",
            }
            if db.salvar_questao(con, q):
                salvas_slug += 1
            else:
                dup_slug += 1

        total_salvas += salvas_slug
        total_duplicadas += dup_slug
        if salvas_slug > 0:
            print(f"[{idx}/{len(pastas_concurso)}] ✅ {slug}: +{salvas_slug} questões C/E importadas ({dup_slug} já existiam)")

    return {
        "total_pastas": len(pastas_concurso),
        "salvas": total_salvas,
        "duplicadas": total_duplicadas,
        "sem_materia": total_sem_materia,
    }


def main():
    pasta_alvo = PASTA_PADRAO
    if len(sys.argv) > 1 and sys.argv[1] == "--pasta" and len(sys.argv) > 2:
        pasta_alvo = Path(sys.argv[2])

    if not pasta_alvo.exists():
        print(f"❌ Pasta {pasta_alvo} não encontrada.")
        print("Se os arquivos estiverem em outro ponto de montagem, use:")
        print("  python -m scripts.importar_lote_cebraspe --pasta /caminho/do/ssd/cebraspe")
        sys.exit(1)

    print("=" * 70)
    print(f"🚀 INICIANDO IMPORTAÇÃO EM LOTE CEBRASPE -> POSTGRESQL")
    print(f"Origem: {pasta_alvo}")
    print("=" * 70)

    con = db.conectar()
    try:
        resultado = importar_pasta(con, pasta_alvo)
        print("\n" + "=" * 70)
        print("🏁 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Pastas processadas : {resultado['total_pastas']}")
        print(f"Novas questões C/E: {resultado['salvas']}")
        print(f"Já existiam no DB  : {resultado['duplicadas']}")
        print(f"Sem matéria segura : {resultado['sem_materia']} (guardrail)")
        print("=" * 70)
    finally:
        con.close()


if __name__ == "__main__":
    main()
