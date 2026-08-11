"""Motor de simulados em PDF: capa, questões numeradas e gabarito comentado."""
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

import db

AZUL = colors.HexColor("#1B3A6B")
CINZA = colors.HexColor("#5A6A85")
PRETO = colors.HexColor("#1E293B")
W, H = A4

_base = getSampleStyleSheet()["Normal"]


def _estilo(nome, **kw):
    padrao = dict(parent=_base, fontSize=10, leading=14, textColor=PRETO)
    padrao.update(kw)
    return ParagraphStyle(nome, **padrao)


e_titulo = _estilo("Titulo", fontSize=20, leading=26, alignment=TA_CENTER,
                   textColor=colors.white, fontName="Helvetica-Bold")
e_sub = _estilo("Sub", fontSize=11, alignment=TA_CENTER,
                textColor=colors.HexColor("#CBD5E1"))
e_num = _estilo("Num", fontName="Helvetica-Bold", textColor=AZUL, fontSize=11,
                spaceBefore=10)
e_origem = _estilo("Origem", fontSize=8, textColor=CINZA)
e_enunciado = _estilo("Enunciado", alignment=TA_JUSTIFY, spaceAfter=4)
e_alt = _estilo("Alt", leftIndent=0.6 * cm)
e_gab = _estilo("Gab", fontSize=9.5, leading=13, spaceAfter=4)


def _capa(materia, quantidade):
    t = Table(
        [[Paragraph("SIMULADO — SEDES/DF", e_titulo)],
         [Paragraph(escape(materia).upper(), e_titulo)],
         [Spacer(1, 0.3 * cm)],
         [Paragraph(f"{quantidade} questões · Gerado em {date.today():%d/%m/%Y}"
                    " · Banca de referência: Instituto Quadrix", e_sub)]],
        colWidths=[W - 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return t


def _origem(q):
    partes = [q.get("banca"), q.get("orgao"), str(q["ano"]) if q.get("ano") else None,
              q.get("assunto")]
    return " · ".join(p for p in partes if p)


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

    doc = SimpleDocTemplate(str(arquivo_saida), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Simulado — {materia}")
    story = [_capa(materia, len(questoes)), Spacer(1, 0.8 * cm)]

    for i, q in enumerate(questoes, 1):
        story.append(Paragraph(f"QUESTÃO {i}", e_num))
        origem = _origem(q)
        if origem:
            story.append(Paragraph(escape(origem), e_origem))
        story.append(Paragraph(escape(q["enunciado"]), e_enunciado))
        for letra in sorted(q["alternativas"]):
            story.append(Paragraph(f"({letra}) {escape(q['alternativas'][letra])}", e_alt))

    story.append(PageBreak())
    story.append(Paragraph("GABARITO COMENTADO", e_num))
    story.append(Spacer(1, 0.2 * cm))
    for i, q in enumerate(questoes, 1):
        letra = q["gabarito"] or "— (gabarito ainda não coletado)"
        linha = f"<b>{i}. {escape(letra)}</b>"
        if q.get("comentario"):
            linha += f" — {escape(q['comentario'])}"
        story.append(Paragraph(linha, e_gab))

    doc.build(story)
    db.marcar_usadas(con, [q["id"] for q in questoes])
    print(f"Simulado gerado: {arquivo_saida} ({len(questoes)} questões)")
    if con_proprio:
        con.close()
    return arquivo_saida
