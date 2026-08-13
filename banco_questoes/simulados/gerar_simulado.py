"""Motor de simulados em PDF: formato de prova de concurso (duas colunas)."""
import hashlib
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, FrameBreak, Image,
                                NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, SimpleDocTemplate, Spacer)

import db

PASTA_IMAGENS = Path(__file__).resolve().parent.parent / "imagens_cache"

CINZA = colors.HexColor("#5A6A85")
PRETO = colors.HexColor("#1E293B")
W, H = A4

MARGEM = 34
CALHA = 16
LARGURA_COL = (W - 2 * MARGEM - CALHA) / 2
ALTURA_CABECALHO = 215  # espaço do cabeçalho na 1ª página (largura cheia)

_base = getSampleStyleSheet()["Normal"]


def _estilo(nome, **kw):
    padrao = dict(parent=_base, fontSize=10, leading=14, textColor=PRETO)
    padrao.update(kw)
    return ParagraphStyle(nome, **padrao)


e_prova_titulo = _estilo("ProvaTitulo", fontName="Helvetica-Bold", fontSize=12,
                         leading=15, alignment=TA_CENTER, textColor=PRETO)
e_prova_sub = _estilo("ProvaSub", fontName="Helvetica-Bold", fontSize=9,
                      leading=12, alignment=TA_CENTER, textColor=PRETO)
e_prova_cargo = _estilo("ProvaCargo", fontSize=8.5, leading=11,
                        alignment=TA_CENTER, textColor=PRETO)
e_aviso = _estilo("Aviso", fontSize=7.5, leading=9.5, alignment=TA_JUSTIFY,
                  textColor=CINZA)
e_instrucoes = _estilo("Instrucoes", fontSize=8, leading=10.5,
                       alignment=TA_JUSTIFY, textColor=PRETO)
e_secao = _estilo("Secao", fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                  alignment=TA_CENTER, textColor=PRETO, spaceBefore=6,
                  spaceAfter=6)
e_questao = _estilo("Questao", fontSize=9.2, leading=11.2,
                    alignment=TA_JUSTIFY, textColor=PRETO, spaceBefore=6,
                    spaceAfter=2)
e_alt = _estilo("Alt", fontSize=9.2, leading=11.2, alignment=TA_JUSTIFY,
                textColor=PRETO, spaceAfter=1)
e_alt.leftIndent = 12
e_alt.firstLineIndent = -12      # recuo pendurado: "(A) " fica pra fora
e_texto_base = _estilo("TextoBase", fontSize=9.2, leading=11.2,
                       alignment=TA_JUSTIFY, textColor=PRETO, spaceAfter=4)
e_chamada_texto = _estilo("ChamadaTexto", fontName="Helvetica-Bold",
                          fontSize=9.2, leading=11.2, textColor=PRETO,
                          spaceBefore=6, spaceAfter=2)
e_origem = _estilo("Origem", fontName="Helvetica-Oblique", fontSize=7,
                   leading=9, textColor=CINZA, spaceAfter=1)
e_gab = _estilo("Gab", fontSize=8.5, leading=10.5, alignment=TA_JUSTIFY,
                textColor=PRETO, spaceAfter=5)


def _imagem(url, largura_max=LARGURA_COL):
    """Baixa (com cache) e devolve a imagem já escalada, ou None se falhar."""
    try:
        sufixo = Path(urlparse(url).path).suffix[:5] or ".png"
        destino = PASTA_IMAGENS / (hashlib.sha1(url.encode()).hexdigest() + sufixo)
        if not destino.exists():
            PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
            resposta = requests.get(url, timeout=30)
            resposta.raise_for_status()
            destino.write_bytes(resposta.content)
        largura, altura = ImageReader(str(destino)).getSize()
        escala = min(1.0, largura_max / largura, (12 * cm) / altura)
        return Image(str(destino), largura * escala, altura * escala)
    except Exception as erro:
        print(f"  (imagem não incluída: {erro.__class__.__name__})")
        return None


def _origem(q):
    partes = [q.get("banca"), q.get("orgao"), str(q["ano"]) if q.get("ano") else None,
              q.get("assunto")]
    return " · ".join(p for p in partes if p)


def _numero_pagina(canvas, doc):
    """Rodapé discreto com o número da página."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawCentredString(W / 2, MARGEM / 2 + 2, str(canvas.getPageNumber()))
    canvas.restoreState()


def _construir_doc(arquivo, titulo):
    doc = BaseDocTemplate(str(arquivo), pagesize=A4,
                          leftMargin=MARGEM, rightMargin=MARGEM,
                          topMargin=MARGEM, bottomMargin=MARGEM, title=titulo)
    altura_total = H - 2 * MARGEM
    altura_pos_cabecalho = altura_total - ALTURA_CABECALHO
    x_direita = MARGEM + LARGURA_COL + CALHA
    primeira = PageTemplate(
        id="primeira",
        frames=[
            Frame(MARGEM, H - MARGEM - ALTURA_CABECALHO, W - 2 * MARGEM,
                  ALTURA_CABECALHO, id="cab", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0),
            Frame(MARGEM, MARGEM, LARGURA_COL, altura_pos_cabecalho, id="e1",
                  leftPadding=0, rightPadding=6, topPadding=0, bottomPadding=0),
            Frame(x_direita, MARGEM, LARGURA_COL, altura_pos_cabecalho, id="d1",
                  leftPadding=6, rightPadding=0, topPadding=0, bottomPadding=0),
        ], onPage=_numero_pagina)
    demais = PageTemplate(
        id="demais",
        frames=[
            Frame(MARGEM, MARGEM, LARGURA_COL, altura_total, id="e",
                  leftPadding=0, rightPadding=6, topPadding=0, bottomPadding=0),
            Frame(x_direita, MARGEM, LARGURA_COL, altura_total, id="d",
                  leftPadding=6, rightPadding=0, topPadding=0, bottomPadding=0),
        ], onPage=_numero_pagina)
    doc.addPageTemplates([primeira, demais])
    return doc


def _cabecalho(materia, quantidade):
    minutos = quantidade * 3
    return [
        Paragraph("SIMULADO — CONCURSO PÚBLICO SEDES/DF", e_prova_titulo),
        Paragraph("SECRETARIA DE ESTADO DE DESENVOLVIMENTO SOCIAL DO DISTRITO FEDERAL",
                  e_prova_sub),
        Paragraph("Cargo 202: TÉCNICO EM DESENVOLVIMENTO E ASSISTÊNCIA SOCIAL (TDAS)"
                  " — ESPECIALIDADE: TÉCNICO ADMINISTRATIVO", e_prova_cargo),
        Paragraph(f"Simulado de treino no estilo da banca Instituto Quadrix — "
                  f"{escape(materia)} — {quantidade} questões", e_prova_cargo),
        Spacer(1, 6),
        Paragraph("Material de estudo NÃO OFICIAL, elaborado com base no conteúdo "
                  "programático do edital de abertura. Não possui vínculo com o "
                  "Instituto Quadrix ou com a SEDES/DF.", e_aviso),
        Spacer(1, 6),
        Paragraph("<b>LEIA AS INSTRUÇÕES:</b>", e_instrucoes),
        Paragraph("Cada questão possui até 5 (cinco) opções de resposta e apenas "
                  "uma resposta correta, conforme o padrão da prova objetiva do "
                  "edital.", e_instrucoes),
        Paragraph(f"Tempo sugerido: {minutos} minutos, sem consulta.", e_instrucoes),
        Paragraph("O gabarito comentado encontra-se ao final do caderno.",
                  e_instrucoes),
    ]


def _questao_flowables(numero, q):
    partes = []
    if q.get("texto_associado") or q.get("imagens"):
        partes.append(Paragraph(f"Texto para a questão {numero}.", e_chamada_texto))
    if q.get("texto_associado"):
        partes.append(Paragraph(escape(q["texto_associado"]), e_texto_base))
    for url in (q.get("imagens") or []):
        figura = _imagem(url, largura_max=LARGURA_COL)
        if figura:
            partes.append(figura)
            partes.append(Spacer(1, 4))
    origem = _origem(q)
    if origem:
        partes.append(Paragraph(escape(origem), e_origem))
    partes.append(Paragraph(
        f"<b>QUESTÃO {numero}.</b> {escape(q['enunciado'])}", e_questao))
    for letra in sorted(q["alternativas"]):
        partes.append(Paragraph(
            f"({letra}) {escape(q['alternativas'][letra])}", e_alt))
    partes.append(Spacer(1, 4))
    return partes


def _gabarito_flowables(questoes):
    partes = [Paragraph("GABARITO COMENTADO", e_secao)]
    for numero, q in enumerate(questoes, 1):
        letra = q.get("gabarito")
        if letra:
            corpo = f"<b>Questão {numero} — {escape(letra)}.</b>"
            if q.get("comentario"):
                corpo += f" {escape(q['comentario'])}"
        else:
            corpo = f"<b>Questão {numero} —</b> (gabarito ainda não coletado)"
        partes.append(Paragraph(corpo, e_gab))
    return partes


def gerar(materia, quantidade, arquivo_saida=None, con=None):
    """Sorteia questões, gera o PDF e marca as usadas. Retorna o caminho ou None."""
    con_proprio = con is None
    if con_proprio:
        con = db.conectar()
    questoes = db.sortear_questoes(con, materia, quantidade)
    if not questoes:
        print(f"Nenhuma questão de '{materia}' no banco. Rode os coletores primeiro.")
        if con_proprio:
            con.close()
        return None

    if arquivo_saida is None:
        nome = materia.lower().replace(" ", "_").replace(",", "")
        arquivo_saida = Path(__file__).resolve().parent / f"simulado_{nome}_{date.today():%Y%m%d}.pdf"
    arquivo_saida = Path(arquivo_saida)

    doc = _construir_doc(arquivo_saida, f"Simulado — {materia}")
    story = [NextPageTemplate("demais")]
    story += _cabecalho(materia, len(questoes))
    story.append(FrameBreak())               # pula do cabeçalho para a 1ª coluna
    story.append(Paragraph(escape(materia).upper(), e_secao))
    for numero, q in enumerate(questoes, 1):
        story += _questao_flowables(numero, q)
    story.append(PageBreak())
    story += _gabarito_flowables(questoes)
    doc.build(story)

    db.marcar_usadas(con, [q["id"] for q in questoes])
    print(f"Simulado gerado: {arquivo_saida} ({len(questoes)} questões)")
    if con_proprio:
        con.close()
    return arquivo_saida


def gerar_completo(quantidade, arquivo_saida=None, con=None):
    """Simulado Geral: distribui a quantidade pelas matérias (edital.PESOS)."""
    import edital
    con_proprio = con is None
    if con_proprio:
        con = db.conectar()
    dist = edital.distribuir_por_peso(quantidade)
    blocos = []
    for materia, n in dist.items():
        if n <= 0:
            continue
        qs = db.sortear_questoes(con, materia, n)
        if qs:
            blocos.append((materia, qs))
    if not blocos:
        print("Nenhuma questão no banco ainda. Rode os coletores primeiro.")
        if con_proprio:
            con.close()
        return None

    total = sum(len(qs) for _, qs in blocos)
    if arquivo_saida is None:
        arquivo_saida = (Path(__file__).resolve().parent
                         / f"simulado_geral_{date.today():%Y%m%d}.pdf")
    arquivo_saida = Path(arquivo_saida)

    doc = SimpleDocTemplate(str(arquivo_saida), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Simulado Geral — SEDES/DF")
    story = [Paragraph("SIMULADO GERAL", e_secao),
             Paragraph(f"{total} questões de todas as matérias", e_questao),
             Spacer(1, 0.8 * cm)]
    numero = 0
    for materia, qs in blocos:
        story.append(Paragraph(escape(materia).upper(), e_secao))
        for q in qs:
            numero += 1
            story.append(Paragraph(f"<b>QUESTÃO {numero}.</b> {escape(q['enunciado'])}", e_questao))
            origem = _origem(q)
            if origem:
                story.append(Paragraph(escape(origem), e_origem))
            for letra in sorted(q["alternativas"]):
                story.append(Paragraph(f"({letra}) {escape(q['alternativas'][letra])}", e_alt))
        story.append(Spacer(1, 0.5 * cm))

    story.append(PageBreak())
    story.append(Paragraph("GABARITO COMENTADO", e_secao))
    numero = 0
    for materia, qs in blocos:
        for q in qs:
            numero += 1
            letra = q["gabarito"] or "— (gabarito ainda não coletado)"
            linha = f"<b>{numero}. {escape(letra)}</b>"
            if q.get("comentario"):
                linha += f" — {escape(q['comentario'])}"
            story.append(Paragraph(linha, e_gab))

    doc.build(story)
    for _, qs in blocos:
        db.marcar_usadas(con, [q["id"] for q in qs])
    print(f"Simulado Geral gerado: {arquivo_saida} ({total} questões)")
    if con_proprio:
        con.close()
    return arquivo_saida
