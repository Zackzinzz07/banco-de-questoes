"""API web do banco de questões. Rodar: ..\\.venv\\Scripts\\python.exe -m uvicorn web_api:app --reload"""
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import edital
from simulados import gerar_simulado

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


@app.get("/api/stats")
def stats():
    con = db.conectar()
    est = db.estatisticas(con)
    con.close()
    return est


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


pasta_web = PASTA / "web"
if pasta_web.exists():
    app.mount("/", StaticFiles(directory=str(pasta_web), html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
