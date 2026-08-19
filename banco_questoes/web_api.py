"""API web do banco de questões. Rodar: ..\\.venv\\Scripts\\python.exe -m uvicorn web_api:app --reload"""
import os
import subprocess
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
    from . import db
    from . import edital
    from . import edital_loader
    from .simulados import gerar_simulado
except ImportError:
    from banco_questoes import db
    from banco_questoes import edital
    from banco_questoes import edital_loader
    from banco_questoes.simulados import gerar_simulado

PASTA = Path(__file__).resolve().parent
PASTA_SIMULADOS = PASTA / "simulados"
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
        "top_categorias": top_cats
    }


@app.get("/api/stats/todas")
def stats_todas():
    """Return statistics for ALL questions in the database."""
    con = db.conectar()

    # Total geral
    total_row = con.execute("SELECT COUNT(*) as cnt FROM questoes").fetchone()
    total = total_row["cnt"] if hasattr(total_row, "__getitem__") else total_row[0]

    # Por órgão
    orgaos = con.execute("SELECT orgao, COUNT(*) as cnt FROM questoes GROUP BY orgao ORDER BY cnt DESC").fetchall()
    por_orgao = {row["orgao"]: row["cnt"] for row in orgaos}

    # Por matéria
    materias = con.execute("SELECT materia, COUNT(*) as cnt FROM questoes GROUP BY materia ORDER BY cnt DESC").fetchall()
    por_materia = {row["materia"]: row["cnt"] for row in materias}

    con.close()

    return {
        "total": total,
        "por_orgao": por_orgao,
        "por_materia": por_materia
    }


@app.get("/api/stats/materias")
def stats_materias():
    """Dashboard: Estatísticas por MATÉRIA com conteúdo (categoria/tema)."""
    con = db.conectar()

    # Total geral
    total_row = con.execute("SELECT COUNT(*) FROM questoes").fetchone()
    total = total_row[0] if total_row else 0

    # Contagem de materias únicas
    materias_unicas = con.execute("SELECT COUNT(DISTINCT materia) FROM questoes WHERE materia IS NOT NULL").fetchone()[0]

    # Contagem de fontes únicas
    fontes_unicas = con.execute("SELECT COUNT(DISTINCT fonte) FROM questoes WHERE fonte IS NOT NULL").fetchone()[0]

    # Contagem de categorias/temas
    categorias_unicas = con.execute("SELECT COUNT(DISTINCT categoria) FROM questoes WHERE categoria IS NOT NULL").fetchone()[0]

    # Por matéria com fontes e categorias
    materias_data = con.execute("""
        SELECT
            materia,
            COUNT(*) as count,
            STRING_AGG(DISTINCT fonte, ', ' ORDER BY fonte) as fontes,
            STRING_AGG(DISTINCT categoria, ', ' ORDER BY categoria LIMIT 3) as categorias
        FROM questoes
        WHERE materia IS NOT NULL
        GROUP BY materia
        ORDER BY count DESC
    """).fetchall()

    por_materia = []
    for row in materias_data:
        por_materia.append({
            "materia": row[0],
            "count": row[1],
            "fontes": row[2],
            "categorias": row[3]
        })

    con.close()

    return {
        "total": total,
        "materias_unicas": materias_unicas,
        "fontes_unicas": fontes_unicas,
        "categorias_unicas": categorias_unicas,
        "por_materia": por_materia
    }


@app.get("/api/materias")
def materias():
    return edital.nomes_materias()


@app.post("/api/simulado/materia")
def simulado_materia(pedido: PedidoMateria):
    from datetime import date
    PASTA_SIMULADOS.mkdir(parents=True, exist_ok=True)
    nome = pedido.materia.lower().replace(" ", "_").replace(",", "") + f"_{date.today():%Y%m%d}.pdf"
    saida = PASTA_SIMULADOS / nome
    con = db.conectar()
    arquivo = gerar_simulado.gerar(pedido.materia, pedido.quantidade, saida, con=con)
    con.close()
    if arquivo is None:
        raise HTTPException(status_code=404, detail=f"Nenhuma questão de '{pedido.materia}'")
    return {"arquivo": arquivo.name}


@app.post("/api/simulado/completo")
def simulado_completo(pedido: PedidoCompleto):
    from datetime import date
    PASTA_SIMULADOS.mkdir(parents=True, exist_ok=True)
    nome = f"simulado_geral_{date.today():%Y%m%d}.pdf"
    saida = PASTA_SIMULADOS / nome
    con = db.conectar()
    arquivo = gerar_simulado.gerar_completo(pedido.quantidade, saida, con=con)
    con.close()
    if arquivo is None:
        raise HTTPException(status_code=404, detail="Nenhuma questão no banco")
    return {"arquivo": arquivo.name}


@app.get("/api/simulados/download/{nome}")
def download_simulado(nome: str):
    nome_seguro = Path(nome).name
    if nome_seguro != nome or nome_seguro.startswith("."):
        raise HTTPException(status_code=400, detail="Nome inválido")
    caminho = PASTA_SIMULADOS / nome_seguro
    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(caminho, media_type="application/pdf", filename=nome_seguro)


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

        return {
            "orgao": orgao,
            "cargo": cargo,
            "materias": list(materias.keys()),
            "pesos": pesos,
            "total_questoes": sum(pesos.values())
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Cargo não encontrado: {cargo}")


@app.post("/api/simulado/cargo/{orgao}/{cargo}")
def gerar_simulado_cargo(orgao: str, cargo: str, pedido: PedidoCargoSimulado):
    """Generate simulado for specific cargo with optional banca filter."""
    from datetime import date
    from pathlib import Path
    from reportlab.platypus import NextPageTemplate, FrameBreak, Paragraph, PageBreak

    try:
        pesos = edital_loader.obter_pesos(orgao, cargo)
        if not pesos:
            raise ValueError("Cargo não encontrado")
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=f"Cargo não encontrado: {str(e)}")

    PASTA_SIMULADOS.mkdir(parents=True, exist_ok=True)

    # Generate filename: simulado_{orgao}_{cargo}_{banca}_{date}.pdf
    nome_cargo_safe = cargo.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")[:20]
    nome_banca_safe = pedido.banca.lower().replace(" ", "_") if pedido.banca else "geral"
    nome = f"simulado_{orgao}_{nome_cargo_safe}_{nome_banca_safe}_{date.today():%Y%m%d}.pdf"
    saida = PASTA_SIMULADOS / nome

    con = db.conectar()

    try:
        from simulados import gerar_simulado as gs
        from xml.sax.saxutils import escape

        # Distribute questions by weight
        questoes_todas = []
        distribuicao = edital_loader.distribuir_por_peso(pedido.quantidade, pesos)

        for materia, quantidade in distribuicao.items():
            if quantidade > 0:
                qs = db.sortear_questoes(
                    con, materia, quantidade,
                    banca=pedido.banca,
                    cargo=cargo,
                    orgao=orgao
                )
                questoes_todas.extend(qs)

        if not questoes_todas:
            raise HTTPException(status_code=404, detail=f"Nenhuma questão encontrada para {orgao}/{cargo}")

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
            "banca": pedido.banca
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
                "SELECT COUNT(*) as c FROM questoes WHERE materia=%s AND cargo=%s",
                (materia, cargo)
            ).fetchone()
            coletadas = linhas["c"] if linhas else 0
            esperadas = pesos.get(materia, 0)
            percentual = round(100 * coletadas / esperadas, 1) if esperadas > 0 else 0

            stats[materia] = {
                "coletadas": coletadas,
                "esperadas": esperadas,
                "percentual": percentual
            }

        total_coletadas = sum(s["coletadas"] for s in stats.values())
        total_esperadas = sum(pesos.values())
        percentual_total = round(100 * total_coletadas / total_esperadas, 1) if total_esperadas > 0 else 0

        return {
            "orgao": orgao,
            "cargo": cargo,
            "materias": stats,
            "total": {
                "coletadas": total_coletadas,
                "esperadas": total_esperadas,
                "percentual": percentual_total
            }
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
            por_categoria[cat] = {
                "total": row["qtd"],
                "temas": {}
            }

        # Para cada categoria, pegar temas
        for categoria in por_categoria.keys():
            cur.execute("""
                SELECT tema, COUNT(*) as qtd,
                       COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
                FROM questoes
                WHERE fonte = 'pci' AND categoria = %s AND tema IS NOT NULL
                GROUP BY tema
                ORDER BY qtd DESC
            """, (categoria,))

            for row in cur.fetchall():
                por_categoria[categoria]["temas"][row["tema"]] = {
                    "total": row["qtd"],
                    "com_imagens": row["com_imagens"]
                }

        return {
            "total_pci": total_pci,
            "por_categoria": por_categoria
        }
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
        cur.execute("""
            SELECT COUNT(*) as total FROM questoes
            WHERE fonte = 'pci' AND categoria = %s
        """, (categoria,))
        total = cur.fetchone()["total"]

        # Por tema
        cur.execute("""
            SELECT tema, COUNT(*) as qtd,
                   COUNT(CASE WHEN imagens_urls != '[]'::jsonb THEN 1 END) as com_imagens
            FROM questoes
            WHERE fonte = 'pci' AND categoria = %s AND tema IS NOT NULL
            GROUP BY tema
            ORDER BY qtd DESC
        """, (categoria,))

        por_tema = {}
        for row in cur.fetchall():
            pct = round((row["com_imagens"] / row["qtd"] * 100), 1) if row["qtd"] > 0 else 0
            por_tema[row["tema"]] = {
                "total": row["qtd"],
                "com_imagens": row["com_imagens"],
                "percentual_imagens": pct
            }

        return {
            "categoria": categoria,
            "total": total,
            "por_tema": por_tema
        }
    finally:
        con.close()


@app.get("/")
def home():
    """Redireciona pra dashboard educacional"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard_educacional.html")


pasta_web = PASTA / "web"
if pasta_web.exists():
    app.mount("/", StaticFiles(directory=str(pasta_web), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
