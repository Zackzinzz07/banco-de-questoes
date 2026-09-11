"""API web do banco de questões.

Rodar (só neste PC):
    python -m uvicorn web_api:app --reload

Rodar (acessível também pelo tablet, na mesma Wi-Fi):
    python -m uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Garantir que o path está correto
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import db
    import edital
    import edital_loader
    from simulados import gerar_simulado
except ImportError:
    from banco_questoes import db, edital, edital_loader
    from banco_questoes.simulados import gerar_simulado

PASTA = Path(__file__).resolve().parent
# Organizada por concurso (orgao/cargo) pra sincronizar certinho com o tablet via Syncthing.
PASTA_SIMULADOS = PASTA / "estudo_autonomo"
COLETA_DISPONIVEL = os.environ.get("COLETA_DISPONIVEL", "1") == "1"

app = FastAPI(title="Banco de Questões SEDES/DF")
_coleta = {"processo": None}


class PedidoMateria(BaseModel):
    materia: str
    quantidade: int = 20


class PedidoCompleto(BaseModel):
    quantidade: int = 60


class PedidoCargoSimulado(BaseModel):
    quantidade: int = 60
    banca: str = None  # Optional banca filter


class PedidoSimuladoV2(BaseModel):
    modo: str = "edital"  # "edital" ou "materia"
    concurso: str | None = None
    cargo: str | None = None
    materia: str | None = None
    banca_estilo: str | None = None  # Compatibilidade legada
    formato: str = "certo_errado"  # "certo_errado" ou "multipla_escolha"
    quantidade: int = 60


@app.get("/api/stats")
def stats():
    con = db.conectar()
    est = db.estatisticas(con)
    con.close()
    return est


@app.get("/api/pci/status")
def pci_status():
    """Status do PCI com categoria/tema."""
    con = db.conectar()

    cur = con.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci'")
    total = cur.fetchone()[0]

    cur = con.execute("SELECT COUNT(*) FROM questoes WHERE fonte='pci' AND categoria IS NOT NULL")
    com_cat = cur.fetchone()[0]

    cur = con.execute("SELECT COUNT(DISTINCT categoria) FROM questoes WHERE fonte='pci'")
    num_cats = cur.fetchone()[0]

    cur = con.execute("""
        SELECT categoria, COUNT(*) as qtd
        FROM questoes
        WHERE fonte='pci'
        GROUP BY categoria
        ORDER BY qtd DESC
        LIMIT 10
    """)

    top_cats = [{"nome": row["categoria"], "total": row["qtd"]} for row in cur.fetchall()]

    con.close()

    return {
        "total": total,
        "com_categoria": com_cat,
        "categorias_unicas": num_cats,
        "top_categorias": top_cats,
    }


@app.get("/api/stats/todas")
def stats_todas():
    """Return statistics for ALL questions in the database."""
    con = db.conectar()

    # Total geral
    total_row = con.execute("SELECT COUNT(*) as cnt FROM questoes").fetchone()
    total = total_row["cnt"] if hasattr(total_row, "__getitem__") else total_row[0]

    # Por órgão
    orgaos = con.execute(
        "SELECT orgao, COUNT(*) as cnt FROM questoes GROUP BY orgao ORDER BY cnt DESC"
    ).fetchall()
    por_orgao = {row["orgao"]: row["cnt"] for row in orgaos}

    # Por matéria
    materias = con.execute(
        "SELECT materia, COUNT(*) as cnt FROM questoes GROUP BY materia ORDER BY cnt DESC"
    ).fetchall()
    por_materia = {row["materia"]: row["cnt"] for row in materias}

    con.close()

    return {"total": total, "por_orgao": por_orgao, "por_materia": por_materia}


@app.get("/api/stats/materias")
def stats_materias():
    """Dashboard: Estatísticas por MATÉRIA com conteúdo (categoria/tema)."""
    con = db.conectar()

    # A conexao usa RealDictCursor: toda linha e dict. Indexar por numero
    # (`linha[0]`) levanta KeyError, entao toda contagem precisa de alias.
    def _contar(sql: str) -> int:
        linha = con.execute(sql).fetchone()
        return linha["n"] if linha else 0

    total = _contar("SELECT COUNT(*) AS n FROM questoes")
    materias_unicas = _contar(
        "SELECT COUNT(DISTINCT materia) AS n FROM questoes WHERE materia IS NOT NULL"
    )
    fontes_unicas = _contar(
        "SELECT COUNT(DISTINCT fonte) AS n FROM questoes WHERE fonte IS NOT NULL"
    )
    categorias_unicas = _contar(
        "SELECT COUNT(DISTINCT categoria) AS n FROM questoes WHERE categoria IS NOT NULL"
    )

    # Por matéria com fontes e categorias.
    # LIMIT nao entra no ORDER BY de agregacao no PostgreSQL -- era erro de
    # sintaxe, e este endpoint devolvia 500 desde que foi escrito. A amostra de
    # 3 categorias sai fatiando o array agregado; sem o corte, materias como
    # Lingua Portuguesa mandariam dezenas de categorias numa string so (o banco
    # tem 433 distintas).
    materias_data = con.execute("""
        SELECT
            materia,
            COUNT(*) AS count,
            STRING_AGG(DISTINCT fonte, ', ' ORDER BY fonte) AS fontes,
            array_to_string(
                (array_agg(DISTINCT categoria) FILTER (WHERE categoria IS NOT NULL))[1:3],
                ', '
            ) AS categorias
        FROM questoes
        WHERE materia IS NOT NULL
        GROUP BY materia
        ORDER BY count DESC
    """).fetchall()

    # A conexao usa RealDictCursor: a linha e dict, nao tupla. row[0] levantava
    # KeyError mesmo depois de a consulta passar.
    por_materia = [
        {
            "materia": row["materia"],
            "count": row["count"],
            "fontes": row["fontes"],
            "categorias": row["categorias"],
        }
        for row in materias_data
    ]

    con.close()

    return {
        "total": total,
        "materias_unicas": materias_unicas,
        "fontes_unicas": fontes_unicas,
        "categorias_unicas": categorias_unicas,
        "por_materia": por_materia,
    }


@app.get("/api/materias")
def materias():
    return edital.nomes_materias()


@app.get("/api/materias/todas")
def materias_todas():
    """Retorna todas as matérias distintas existentes no acervo."""
    con = db.conectar()
    try:
        cur = con.execute(
            "SELECT DISTINCT materia FROM questoes WHERE materia IS NOT NULL ORDER BY materia"
        )
        return [r["materia"] for r in cur.fetchall()]
    finally:
        con.close()


@app.post("/api/v2/simulado/gerar")
def gerar_simulado_v2(pedido: PedidoSimuladoV2):
    """Endpoint unificado para geração de simulados em formato universal
    (Certo/Errado ou Múltipla Escolha).
    """
    # Mapeamento estrito para os 2 formatos universais
    raw_formato = (pedido.formato or pedido.banca_estilo or "certo_errado").lower().strip()
    if raw_formato in ["cebraspe", "cespe", "julgar", "certo_errado", "certo-errado"]:
        formato = "certo_errado"
    else:
        formato = "multipla_escolha"

    con = db.conectar()
    try:
        if pedido.modo == "edital":
            if not pedido.concurso:
                raise HTTPException(
                    status_code=400, detail="Campo 'concurso' é obrigatório no modo edital"
                )
            cargos = edital_loader.listar_cargos(pedido.concurso)
            if not cargos:
                raise HTTPException(
                    status_code=404, detail=f"Concurso '{pedido.concurso}' não encontrado"
                )
            cargo_alvo = pedido.cargo or cargos[0]
            pesos = edital_loader.obter_pesos(pedido.concurso, cargo_alvo)
            if not pesos:
                raise HTTPException(
                    status_code=404, detail=f"Pesos não encontrados para o cargo '{cargo_alvo}'"
                )

            from simulados import por_edital
            from simulados.gerador_multibanca import GeradorSimuladoMultiBanca

            dados_edital = edital_loader.carregar_edital(pedido.concurso) or {}
            formato_alvo = pedido.formato or dados_edital.get("formato") or formato
            banca_edital = dados_edital.get("banca")

            sim = por_edital.montar(
                con,
                pesos,
                pedido.quantidade,
                formato=formato_alvo,
                banca=banca_edital,
            )
            if not sim.questoes:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Nenhuma questão encontrada com o formato '{formato_alvo}' "
                        f"para o concurso '{pedido.concurso}'. "
                        "Execute a importação das questões no banco de dados."
                    ),
                )
            gerador = GeradorSimuladoMultiBanca(
                formato,
                con=con,
                concurso=pedido.concurso,
                cargo=cargo_alvo,
            )
            nome_arquivo = f"simulado_{pedido.concurso}_{formato}_{pedido.quantidade}q.pdf"
            subpasta = PASTA_SIMULADOS / pedido.concurso
            subpasta.mkdir(parents=True, exist_ok=True)
            saida = subpasta / nome_arquivo
            gerador.gerar(pedido.quantidade, saida, questoes=sim.questoes)

            return {
                "sucesso": True,
                "arquivo": nome_arquivo,
                "url_download": f"/api/simulados/download/{nome_arquivo}",
                "questoes_geradas": len(sim.questoes),
                "lacunas": sim.lacunas,
            }

        elif pedido.modo == "materia":
            if not pedido.materia:
                raise HTTPException(
                    status_code=400, detail="Campo 'materia' é obrigatório no modo matéria"
                )

            from simulados.gerador_multibanca import GeradorSimuladoMultiBanca

            questoes = db.sortear_questoes(
                con, pedido.materia, pedido.quantidade, formato=formato
            )
            if not questoes:
                questoes = db.sortear_questoes(
                    con, pedido.materia, pedido.quantidade
                )
            if not questoes:
                raise HTTPException(
                    status_code=404,
                    detail=f"Nenhuma questão encontrada para a matéria '{pedido.materia}'",
                )

            gerador = GeradorSimuladoMultiBanca(
                formato,
                con=con,
                concurso_nome=f"SIMULADO — {pedido.materia.upper()}",
            )
            materia_slug = (
                pedido.materia.lower()
                .replace(" ", "_")
                .replace(",", "")
                .replace("/", "_")
                .replace("(", "")
                .replace(")", "")[:20]
            )
            nome_arquivo = f"treino_{materia_slug}_{formato}_{pedido.quantidade}q.pdf"
            subpasta = PASTA_SIMULADOS / "_por_materia" / materia_slug
            subpasta.mkdir(parents=True, exist_ok=True)
            saida = subpasta / nome_arquivo
            gerador.gerar(pedido.quantidade, saida, questoes=questoes)

            lacunas = {}
            if len(questoes) < pedido.quantidade:
                lacunas[pedido.materia] = pedido.quantidade - len(questoes)

            return {
                "sucesso": True,
                "arquivo": nome_arquivo,
                "url_download": f"/api/simulados/download/{nome_arquivo}",
                "questoes_geradas": len(questoes),
                "lacunas": lacunas,
            }
        else:
            raise HTTPException(status_code=400, detail=f"Modo '{pedido.modo}' inválido")
    finally:
        con.close()


@app.post("/api/simulado/materia")
def simulado_materia(pedido: PedidoMateria):
    from datetime import date

    materia_slug = pedido.materia.lower().replace(" ", "_").replace(",", "")
    subpasta = PASTA_SIMULADOS / "_por_materia" / materia_slug
    subpasta.mkdir(parents=True, exist_ok=True)
    nome = f"{materia_slug}_{date.today():%Y%m%d}.pdf"
    saida = subpasta / nome
    con = db.conectar()
    arquivo = gerar_simulado.gerar(pedido.materia, pedido.quantidade, saida, con=con)
    con.close()
    if arquivo is None:
        raise HTTPException(status_code=404, detail=f"Nenhuma questão de '{pedido.materia}'")
    return {"arquivo": arquivo.name}


@app.post("/api/simulado/completo")
def simulado_completo(pedido: PedidoCompleto):
    from datetime import date

    subpasta = PASTA_SIMULADOS / "_geral"
    subpasta.mkdir(parents=True, exist_ok=True)
    nome = f"simulado_geral_{date.today():%Y%m%d}.pdf"
    saida = subpasta / nome
    con = db.conectar()
    arquivo = gerar_simulado.gerar_completo(pedido.quantidade, saida, con=con)
    con.close()
    if arquivo is None:
        raise HTTPException(status_code=404, detail="Nenhuma questão no banco")
    return {"arquivo": arquivo.name}


@app.api_route("/api/simulados/download/{nome}", methods=["GET", "HEAD"])
def download_simulado(nome: str, inline: bool = False):
    nome_seguro = Path(nome).name
    if nome_seguro != nome or nome_seguro.startswith("."):
        raise HTTPException(status_code=400, detail="Nome inválido")
    caminho = None
    if PASTA_SIMULADOS.exists():
        caminho = next(PASTA_SIMULADOS.rglob(nome_seguro), None)
    if caminho is None and (PASTA / nome_seguro).exists():
        caminho = PASTA / nome_seguro
    if caminho is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    if inline:
        headers = {"Content-Disposition": f'inline; filename="{nome_seguro}"'}
        return FileResponse(caminho, media_type="application/pdf", headers=headers)
    return FileResponse(caminho, media_type="application/pdf", filename=nome_seguro)


@app.get("/api/simulados/recentes")
def simulados_recentes():
    """Lista simulados recentes para abertura rápida no tablet."""
    arquivos = []
    pastas_busca = [PASTA_SIMULADOS]
    if PASTA.exists():
        pastas_busca.append(PASTA)
    nomes_vistos = set()
    for pasta in pastas_busca:
        if not pasta.exists():
            continue
        padrao = "*.pdf" if pasta == PASTA_SIMULADOS else "simulado_*.pdf"
        for pdf in pasta.glob(padrao) if pasta == PASTA else pasta.rglob("*.pdf"):
            if pdf.name in nomes_vistos:
                continue
            nomes_vistos.add(pdf.name)
            try:
                st = pdf.stat()
                arquivos.append(
                    {
                        "nome": pdf.name,
                        "tamanho_kb": round(st.st_size / 1024, 1),
                        "data": st.st_mtime,
                    }
                )
            except OSError:
                continue
    arquivos.sort(key=lambda x: x["data"], reverse=True)
    return arquivos[:15]



@app.post("/api/simulados/zerar")
def zerar_simulados():
    con = db.conectar()
    db.zerar_usadas(con)
    con.close()
    return {"ok": True}


@app.post("/api/coletar")
def coletar():
    if not COLETA_DISPONIVEL:
        raise HTTPException(status_code=503, detail="Coleta fora do Docker. Rode de seu host.")
    return {"ok": True}


# ============================================================================
# CARGO-BASED ENDPOINTS (NEW)
# ============================================================================


@app.get("/api/orgaos")
def listar_orgaos():
    """Return list of all available órgãos/concursos."""
    orgaos = edital_loader.listar_concursos()
    return {"orgaos": orgaos}


@app.get("/api/cargos/{orgao}")
def listar_cargos_por_orgao(orgao: str):
    """Return cargos available for given órgão."""
    cargos = edital_loader.listar_cargos(orgao)
    if not cargos:
        raise HTTPException(status_code=404, detail=f"Órgão não encontrado: {orgao}")
    return {"orgao": orgao, "cargos": cargos}


@app.get("/api/materias/{orgao}/{cargo}")
def listar_materias_por_cargo(orgao: str, cargo: str):
    """Return materias and weights for specific cargo."""
    try:
        materias = edital_loader.obter_materias(orgao, cargo)
        pesos = edital_loader.obter_pesos(orgao, cargo)

        if materias is None or pesos is None:
            raise ValueError("Cargo não encontrado")

        dados_edital = edital_loader.carregar_edital(orgao) or {}
        return {
            "orgao": orgao,
            "cargo": cargo,
            "materias": list(materias.keys()),
            "pesos": pesos,
            "total_questoes": sum(pesos.values()),
            "formato": dados_edital.get("formato", "Multipla_Escolha"),
            "banca": dados_edital.get("banca", "Cebraspe"),
        }
    except (FileNotFoundError, ValueError) as erro:
        raise HTTPException(status_code=404, detail=f"Cargo não encontrado: {cargo}") from erro


@app.post("/api/simulado/cargo/{orgao}/{cargo}")
def gerar_simulado_cargo(orgao: str, cargo: str, pedido: PedidoCargoSimulado):
    """Generate simulado for specific cargo with optional banca filter."""
    from datetime import date

    from reportlab.platypus import FrameBreak, NextPageTemplate, PageBreak, Paragraph

    try:
        pesos = edital_loader.obter_pesos(orgao, cargo)
        if not pesos:
            raise ValueError("Cargo não encontrado")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Cargo não encontrado: {str(e)}")

    # Organiza por concurso: estudo_autonomo/{orgao}/{cargo}/simulado_{banca}_{data}.pdf
    nome_cargo_safe = (
        cargo.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")[:20]
    )
    nome_banca_safe = pedido.banca.lower().replace(" ", "_") if pedido.banca else "geral"
    subpasta = PASTA_SIMULADOS / orgao / nome_cargo_safe
    subpasta.mkdir(parents=True, exist_ok=True)
    nome = f"simulado_{nome_banca_safe}_{date.today():%Y%m%d}.pdf"
    saida = subpasta / nome

    con = db.conectar()

    try:
        from xml.sax.saxutils import escape

        from simulados import gerar_simulado as gs

        # Distribute questions by weight
        questoes_todas = []
        distribuicao = edital_loader.distribuir_por_peso(pedido.quantidade, pesos)

        for materia, quantidade in distribuicao.items():
            if quantidade > 0:
                qs = db.sortear_questoes(
                    con, materia, quantidade, banca=pedido.banca, cargo=cargo, orgao=orgao
                )
                questoes_todas.extend(qs)

        if not questoes_todas:
            raise HTTPException(
                status_code=404, detail=f"Nenhuma questão encontrada para {orgao}/{cargo}"
            )

        # Build PDF using gerar_simulado's internal functions
        doc = gs._construir_doc(saida, f"Simulado — {cargo}")
        story = [NextPageTemplate("demais")]
        story += gs._cabecalho(cargo, len(questoes_todas))
        story.append(FrameBreak())
        story.append(Paragraph(escape(cargo).upper(), gs.e_secao))

        for numero, q in enumerate(questoes_todas, 1):
            story += gs._questao_flowables(numero, q)

        story.append(PageBreak())
        story += gs._gabarito_flowables(questoes_todas)
        doc.build(story)

        # Mark as used
        ids_usadas = [q["id"] for q in questoes_todas]
        db.marcar_usadas(con, ids_usadas)

        return {
            "arquivo": saida.name,
            "orgao": orgao,
            "cargo": cargo,
            "quantidade": len(questoes_todas),
            "banca": pedido.banca,
        }
    finally:
        con.close()


@app.get("/api/stats/cargo/{orgao}/{cargo}")
def stats_cargo(orgao: str, cargo: str):
    """Return statistics (question count) for specific cargo."""
    try:
        materias = edital_loader.obter_materias(orgao, cargo)
        pesos = edital_loader.obter_pesos(orgao, cargo)

        if materias is None or pesos is None:
            raise ValueError("Cargo não encontrado")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    con = db.conectar()

    try:
        stats = {}
        for materia in materias.keys():
            # Count questions for this materia/cargo combination
            linhas = con.execute(
                "SELECT COUNT(*) as c FROM questoes WHERE materia=%s AND cargo=%s", (materia, cargo)
            ).fetchone()
            coletadas = linhas["c"] if linhas else 0
            esperadas = pesos.get(materia, 0)
            percentual = round(100 * coletadas / esperadas, 1) if esperadas > 0 else 0

            stats[materia] = {
                "coletadas": coletadas,
                "esperadas": esperadas,
                "percentual": percentual,
            }

        total_coletadas = sum(s["coletadas"] for s in stats.values())
        total_esperadas = sum(pesos.values())
        percentual_total = (
            round(100 * total_coletadas / total_esperadas, 1) if total_esperadas > 0 else 0
        )

        return {
            "orgao": orgao,
            "cargo": cargo,
            "materias": stats,
            "total": {
                "coletadas": total_coletadas,
                "esperadas": total_esperadas,
                "percentual": percentual_total,
            },
        }
    finally:
        con.close()


@app.get("/api/stats/pci")
def stats_pci_global():
    """Estatisticas do PCI: total + por categoria."""
    con = db.conectar()
    try:
        from psycopg2.extras import RealDictCursor

        cur = con.cursor(cursor_factory=RealDictCursor)

        # Total PCI
        cur.execute("SELECT COUNT(*) as total FROM questoes WHERE fonte = 'pci'")
        total_pci = cur.fetchone()["total"]

        # Por categoria
        cur.execute("""
            SELECT categoria, COUNT(*) as qtd
            FROM questoes
            WHERE fonte = 'pci' AND categoria IS NOT NULL
            GROUP BY categoria
            ORDER BY qtd DESC
        """)

        por_categoria = {}
        for row in cur.fetchall():
            cat = row["categoria"]
            por_categoria[cat] = {"total": row["qtd"], "temas": {}}

        # Para cada categoria, pegar temas
        for categoria in por_categoria.keys():
            cur.execute(
                """
                SELECT tema, COUNT(*) as qtd,
                       COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
                FROM questoes
                WHERE fonte = 'pci' AND categoria = %s AND tema IS NOT NULL
                GROUP BY tema
                ORDER BY qtd DESC
            """,
                (categoria,),
            )

            for row in cur.fetchall():
                por_categoria[categoria]["temas"][row["tema"]] = {
                    "total": row["qtd"],
                    "com_imagens": row["com_imagens"],
                }

        return {"total_pci": total_pci, "por_categoria": por_categoria}
    finally:
        con.close()


@app.get("/api/stats/pci/{categoria}")
def stats_pci_categoria(categoria: str):
    """Estatisticas de uma categoria especifica do PCI."""
    con = db.conectar()
    try:
        from psycopg2.extras import RealDictCursor

        cur = con.cursor(cursor_factory=RealDictCursor)

        # Total categoria
        cur.execute(
            """
            SELECT COUNT(*) as total FROM questoes
            WHERE fonte = 'pci' AND categoria = %s
        """,
            (categoria,),
        )
        total = cur.fetchone()["total"]

        # Por tema
        cur.execute(
            """
            SELECT tema, COUNT(*) as qtd,
                   COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
            FROM questoes
            WHERE fonte = 'pci' AND categoria = %s AND tema IS NOT NULL
            GROUP BY tema
            ORDER BY qtd DESC
        """,
            (categoria,),
        )

        por_tema = {}
        for row in cur.fetchall():
            pct = round((row["com_imagens"] / row["qtd"] * 100), 1) if row["qtd"] > 0 else 0
            por_tema[row["tema"]] = {
                "total": row["qtd"],
                "com_imagens": row["com_imagens"],
                "percentual_imagens": pct,
            }

        return {"categoria": categoria, "total": total, "por_tema": por_tema}
    finally:
        con.close()


@app.get("/")
def home():
    """Redireciona para o gerador de simulados."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/index.html")


pasta_web = PASTA / "web"
if pasta_web.exists():
    app.mount("/", StaticFiles(directory=str(pasta_web), html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
