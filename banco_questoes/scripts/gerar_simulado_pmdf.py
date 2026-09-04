"""Gerador de simulado PMDF — Soldado Policial Militar (Banca Cebraspe, 120 questões).

Gera o caderno de prova em PDF com layout profissional Cebraspe:
- 2 colunas com linha divisória vertical contínua
- Cabeçalho oficial com dados da PMDF e Cebraspe
- Distribuição de 120 questões conforme edital
- Gabarito comentado ao final
"""

from datetime import date
from pathlib import Path
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

# Ajuste de path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db
import edital_loader

W, H = A4
MARGEM = 34
CALHA = 16
LARGURA_COL = (W - 2 * MARGEM - CALHA) / 2
ALTURA_CABECALHO = 195

PRETO = colors.HexColor("#1A1A1A")
CINZA_ESCURO = colors.HexColor("#333333")
CINZA_LINHA = colors.HexColor("#888888")

_base = getSampleStyleSheet()["Normal"]


def _estilo(nome, **kw):
    p = dict(parent=_base, fontSize=9.5, leading=13, textColor=PRETO)
    p.update(kw)
    return ParagraphStyle(nome, **p)


e_titulo = _estilo("Tit", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=TA_CENTER)
e_sub = _estilo("Sub", fontName="Helvetica-Bold", fontSize=10, leading=14, alignment=TA_CENTER)
e_cargo = _estilo("Car", fontName="Helvetica", fontSize=9, leading=12, alignment=TA_CENTER)
e_instrucoes = _estilo("Inst", fontName="Helvetica-Oblique", fontSize=8, leading=11, alignment=TA_JUSTIFY)
e_secao = _estilo("Sec", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#0D47A1"))
e_questao = _estilo("Q", fontName="Times-Roman", fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY)
e_ce = _estilo("CE", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#263238"))
e_alt = _estilo("Alt", fontName="Times-Roman", fontSize=8.8, leading=12, alignment=TA_JUSTIFY)
e_origem = _estilo("Ori", fontName="Helvetica-Oblique", fontSize=7.5, leading=10, textColor=colors.HexColor("#607D8B"))
e_texto_base = _estilo("Txt", fontName="Times-Italic", fontSize=8.8, leading=12, alignment=TA_JUSTIFY)
e_gab = _estilo("Gab", fontName="Helvetica", fontSize=8.5, leading=12)


def _on_page_cebraspe(canvas, doc):
    canvas.saveState()
    # Divisor vertical entre as duas colunas
    x_linha = MARGEM + LARGURA_COL + CALHA / 2
    if doc.page == 1:
        y_topo_linha = H - MARGEM - ALTURA_CABECALHO - 10
    else:
        y_topo_linha = H - MARGEM
    y_fundo_linha = MARGEM + 15
    canvas.setStrokeColor(CINZA_LINHA)
    canvas.setLineWidth(0.5)
    canvas.line(x_linha, y_fundo_linha, x_linha, y_topo_linha)

    # Rodapé estilo Cebraspe: "- 1 -", "- 2 -"
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(CINZA_ESCURO)
    canvas.drawCentredString(W / 2, MARGEM / 2, f"- {doc.page} -")
    canvas.drawString(MARGEM, MARGEM / 2, "PMDF / CFP — SOLDADO")
    canvas.drawRightString(W - MARGEM, MARGEM / 2, "CEBRASPE")
    canvas.restoreState()


def _construir_doc_pmdf(arquivo):
    doc = BaseDocTemplate(
        str(arquivo),
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=MARGEM,
        bottomMargin=MARGEM,
        title="Simulado PMDF — Soldado Policial Militar",
    )
    altura_total = H - 2 * MARGEM
    altura_pos_cabecalho = altura_total - ALTURA_CABECALHO
    x_direita = MARGEM + LARGURA_COL + CALHA

    primeira = PageTemplate(
        id="primeira",
        frames=[
            Frame(MARGEM, H - MARGEM - ALTURA_CABECALHO, W - 2 * MARGEM, ALTURA_CABECALHO, id="cab",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
            Frame(MARGEM, MARGEM, LARGURA_COL, altura_pos_cabecalho, id="e1",
                  leftPadding=0, rightPadding=6, topPadding=0, bottomPadding=0),
            Frame(x_direita, MARGEM, LARGURA_COL, altura_pos_cabecalho, id="d1",
                  leftPadding=6, rightPadding=0, topPadding=0, bottomPadding=0),
        ],
        onPage=_on_page_cebraspe,
    )

    demais = PageTemplate(
        id="demais",
        frames=[
            Frame(MARGEM, MARGEM, LARGURA_COL, altura_total, id="e",
                  leftPadding=0, rightPadding=6, topPadding=0, bottomPadding=0),
            Frame(x_direita, MARGEM, LARGURA_COL, altura_total, id="d",
                  leftPadding=6, rightPadding=0, topPadding=0, bottomPadding=0),
        ],
        onPage=_on_page_cebraspe,
    )

    doc.addPageTemplates([primeira, demais])
    return doc


def coletar_questoes_pmdf(con, total_desejado=120):
    """Puxa 120 questões distribuídas pelas matérias do edital da PMDF."""
    distribuicao = [
        ("Língua Portuguesa", ["Língua Portuguesa"], 15),
        ("Matemática e Raciocínio Lógico", ["Raciocínio Lógico", "Matemática"], 8),
        ("Língua Inglesa", ["Inglês"], 5),
        ("Noções de Informática Operacional", ["Noções de Informática", "Informática"], 6),
        ("Legislação Específica da PMDF e RIDE", ["Conhecimentos do DF e Legislação", "Legislação Específica"], 16),
        ("Noções de Direito Constitucional", ["Direito Constitucional"], 14),
        ("Noções de Direito Administrativo", ["Direito Administrativo"], 12),
        ("Direito Penal e Processual Penal", ["Direito Penal", "Direito Processual Penal"], 20),
        ("Noções de Direito Penal Militar", ["Direito Penal Militar", "Direito Processual Penal Militar"], 14),
        ("Direitos Humanos e Criminologia", ["Direito Constitucional", "Direito Penal"], 10),
    ]

    questoes_finais = []
    ids_vistos = set()

    for bloco, materias, qtd in distribuicao:
        bloco_qs = []
        # 1ª prioridade: C/E da Cebraspe
        for mat in materias:
            if len(bloco_qs) >= qtd:
                break
            faltam = qtd - len(bloco_qs)
            cur = con.execute("""
                SELECT * FROM questoes
                WHERE materia = %s
                  AND (banca ILIKE '%%cebraspe%%' OR banca ILIKE '%%cespe%%')
                  AND gabarito IN ('C', 'E', 'CERTO', 'ERRADO')
                  AND content_hash IS NOT NULL
                ORDER BY RANDOM()
                LIMIT %s
            """, (mat, faltam * 2))
            for q in cur.fetchall():
                if q["id"] not in ids_vistos and len(bloco_qs) < qtd:
                    ids_vistos.add(q["id"])
                    d = dict(q)
                    d["bloco_nome"] = bloco
                    bloco_qs.append(d)

        # 2ª prioridade: Qualquer C/E da matéria
        if len(bloco_qs) < qtd:
            for mat in materias:
                if len(bloco_qs) >= qtd:
                    break
                faltam = qtd - len(bloco_qs)
                cur = con.execute("""
                    SELECT * FROM questoes
                    WHERE materia = %s
                      AND gabarito IN ('C', 'E', 'CERTO', 'ERRADO')
                      AND content_hash IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (mat, faltam * 2))
                for q in cur.fetchall():
                    if q["id"] not in ids_vistos and len(bloco_qs) < qtd:
                        ids_vistos.add(q["id"])
                        d = dict(q)
                        d["bloco_nome"] = bloco
                        bloco_qs.append(d)

        # 3ª prioridade: Qualquer questão da matéria
        if len(bloco_qs) < qtd:
            for mat in materias:
                if len(bloco_qs) >= qtd:
                    break
                faltam = qtd - len(bloco_qs)
                cur = con.execute("""
                    SELECT * FROM questoes
                    WHERE materia = %s AND content_hash IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (mat, faltam * 2))
                for q in cur.fetchall():
                    if q["id"] not in ids_vistos and len(bloco_qs) < qtd:
                        ids_vistos.add(q["id"])
                        d = dict(q)
                        d["bloco_nome"] = bloco
                        bloco_qs.append(d)

        questoes_finais.extend(bloco_qs)

    return questoes_finais[:total_desejado]


def gerar_pdf_pmdf(saida_path: Path):
    """Gera o PDF completo de 120 questões para Soldado da PMDF."""
    saida_path.parent.mkdir(parents=True, exist_ok=True)
    con = db.conectar()

    try:
        questoes = coletar_questoes_pmdf(con, total_desejado=120)
        doc = _construir_doc_pmdf(saida_path)

        story = [NextPageTemplate("demais")]

        # Cabeçalho da Prova
        story += [
            Paragraph("POLÍCIA MILITAR DO DISTRITO FEDERAL — PMDF", e_titulo),
            Paragraph("CURSO DE FORMAÇÃO DE PRAÇAS (CFP) — SOLDADO POLICIAL MILITAR", e_sub),
            Paragraph("PROVA OBJETIVA — BANCA EXAMINADORA: CEBRASPE", e_cargo),
            Spacer(1, 6),
            Paragraph(
                "<b>LEIA COM ATENÇÃO AS INSTRUÇÕES:</b><br/>"
                "1. Este caderno contém 120 itens avaliados no formato Certo (C) ou Errado (E).<br/>"
                "2. Conforme o edital padrão Cebraspe, um item marcado em discordância com o gabarito oficial anula a pontuação de um item correto.<br/>"
                "3. O gabarito oficial comentado encontra-se ao final deste caderno de questões.",
                e_instrucoes,
            ),
            Spacer(1, 8),
        ]
        story.append(FrameBreak())

        bloco_atual = None
        for i, q in enumerate(questoes, 1):
            bloco = q.get("bloco_nome")
            if bloco != bloco_atual:
                bloco_atual = bloco
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"■ {escape(bloco.upper())}", e_secao))
                story.append(Spacer(1, 4))

            # Texto associado se houver
            if q.get("texto_associado"):
                story.append(Paragraph(escape(q["texto_associado"][:400]), e_texto_base))
                story.append(Spacer(1, 2))

            # Origem
            banca_str = q.get("banca") or "Cebraspe"
            ano_str = str(q.get("ano") or "")
            origem = f"[{banca_str} • {ano_str}]" if ano_str else f"[{banca_str}]"
            story.append(Paragraph(escape(origem), e_origem))

            # Enunciado
            story.append(Paragraph(f"<b>ITEM {i}.</b> {escape(q['enunciado'])}", e_questao))

            # Se for C/E
            is_ce = q.get("gabarito") in ("C", "E", "CERTO", "ERRADO")
            if is_ce:
                story.append(Paragraph("( &nbsp; ) CERTO &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ( &nbsp; ) ERRADO", e_ce))
            else:
                alts = q.get("alternativas") or {}
                if isinstance(alts, str):
                    import json
                    try:
                        alts = json.loads(alts)
                    except Exception:
                        alts = {}
                if isinstance(alts, dict):
                    for letra in sorted(alts):
                        story.append(Paragraph(f"<b>({letra})</b> {escape(str(alts[letra]))}", e_alt))

            story.append(Spacer(1, 6))

        # Folha de Respostas e Gabarito
        story.append(PageBreak())
        story.append(Paragraph("GABARITO OFICIAL COMENTADO — PMDF SOLDADO", e_titulo))
        story.append(Spacer(1, 10))

        for i, q in enumerate(questoes, 1):
            gab = q.get("gabarito") or "—"
            if gab in ("C", "CERTO"):
                gab_fmt = "CERTO"
            elif gab in ("E", "ERRADO"):
                gab_fmt = "ERRADO"
            else:
                gab_fmt = gab

            comentario = q.get("comentario") or ""
            texto_gab = f"<b>Item {i}: {gab_fmt}</b>"
            if comentario:
                texto_gab += f" — {escape(comentario[:250])}"
            story.append(Paragraph(texto_gab, e_gab))
            story.append(Spacer(1, 3))

        doc.build(story)
        print(f"✅ Simulado PMDF gerado: {saida_path} ({len(questoes)} questões)")
        return saida_path

    finally:
        con.close()


if __name__ == "__main__":
    destino = ROOT / "testes_pdf" / "pmdf_soldado" / "simulado_pmdf_soldado_cebraspe_120q.pdf"
    gerar_pdf_pmdf(destino)
