"""Coletor de provas em PDF da Quadrix: baixa, extrai questões e casa gabaritos."""
import re
import sys
from pathlib import Path

import pdfplumber
import requests

import db
import edital

RE_QUESTAO = re.compile(r"QUEST[ÃA]O\s+(\d+)")
RE_ALTERNATIVA = re.compile(r"\(([A-E])\)")

PASTA_PDFS = Path(__file__).resolve().parent / "provas_pdf"
ARQUIVO_RELATORIO = Path(__file__).resolve().parent / "relatorio_extracao.txt"

# Provas encerradas da Quadrix com matérias em comum com o edital (nível médio).
# Preencher pesquisando em https://www.quadrix.org.br (concursos encerrados):
# cada item precisa da URL do caderno de prova e do gabarito definitivo.
PROVAS = [
    # {"nome": "crt4_2024_assistente", "orgao": "CRT-4", "ano": 2024,
    #  "prova": "Assistente Administrativo",
    #  "url_prova": "https://.../caderno.pdf", "url_gabarito": "https://.../gabarito.pdf"},
]


def _mapear_secoes(texto):
    """Posições onde cada matéria começa (títulos de seção em linha própria, MAIÚSCULA)."""
    marcas = []
    pos = 0
    for linha in texto.splitlines(keepends=True):
        limpa = " ".join(linha.split())
        eh_titulo = (limpa and limpa == limpa.upper() and len(limpa) <= 60
                     and any(c.isalpha() for c in limpa))
        if eh_titulo:
            for nome, dados in edital.MATERIAS.items():
                if any(padrao in limpa for padrao in dados["titulos_pdf"]):
                    marcas.append((pos, nome))
                    break
        pos += len(linha)
    return sorted(marcas)


def _materia_na_posicao(marcas, pos):
    atual = None
    for inicio, nome in marcas:
        if inicio <= pos:
            atual = nome
        else:
            break
    return atual


def _limpar(texto):
    return " ".join(texto.split()).strip()


def extrair_questoes_do_texto(texto):
    """Retorna (questoes, numeros_pulados). Questão sem 2+ alternativas é pulada."""
    marcas = _mapear_secoes(texto)
    achados = list(RE_QUESTAO.finditer(texto))
    questoes, puladas = [], []
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        corpo = texto[m.end():fim]
        numero = int(m.group(1))
        partes = RE_ALTERNATIVA.split(corpo)
        enunciado = _limpar(partes[0])
        alternativas = {}
        for letra, trecho in zip(partes[1::2], partes[2::2]):
            alternativas[letra] = _limpar(trecho)
        if not enunciado or len(alternativas) < 2:
            puladas.append(numero)
            continue
        questoes.append({
            "numero": numero,
            "enunciado": enunciado,
            "alternativas": alternativas,
            "materia": _materia_na_posicao(marcas, m.start()),
        })
    return questoes, puladas


def extrair_gabarito_de_tabelas(tabelas):
    """Tabelas do PDF de gabarito: linha de números seguida de linha de letras."""
    gabarito = {}
    for tabela in tabelas:
        for linha_num, linha_resp in zip(tabela, tabela[1:]):
            for num, resp in zip(linha_num, linha_resp):
                num = str(num or "").strip()
                resp = str(resp or "").strip().upper()
                if num.isdigit() and len(resp) == 1 and resp in "ABCDE":
                    gabarito[int(num)] = resp
    return gabarito


def casar_gabarito(questoes, gabarito):
    for q in questoes:
        q["gabarito"] = gabarito.get(q["numero"])


def _texto_do_pdf(caminho):
    with pdfplumber.open(caminho) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _tabelas_do_pdf(caminho):
    with pdfplumber.open(caminho) as pdf:
        tabelas = []
        for pagina in pdf.pages:
            tabelas.extend(pagina.extract_tables())
        return tabelas


def baixar(url, destino):
    """Baixa a URL para destino, usando cache local (não re-baixa)."""
    destino = Path(destino)
    if destino.exists():
        return destino
    resposta = requests.get(url, timeout=60)
    resposta.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resposta.content)
    return destino


def processar_prova(caminho_prova, caminho_gabarito, con, metadados):
    """Extrai as questões de uma prova, casa o gabarito e salva no banco."""
    questoes, puladas = extrair_questoes_do_texto(_texto_do_pdf(caminho_prova))
    casar_gabarito(questoes, extrair_gabarito_de_tabelas(_tabelas_do_pdf(caminho_gabarito)))
    resultado = {"salvas": 0, "duplicadas": 0, "puladas": puladas, "sem_materia": 0}
    for q in questoes:
        if q["materia"] is None:
            resultado["sem_materia"] += 1
            continue
        salvou = db.salvar_questao(con, {
            "id_qc": None,
            "enunciado": q["enunciado"],
            "alternativas": q["alternativas"],
            "gabarito": q["gabarito"],
            "materia": q["materia"],
            "banca": metadados.get("banca", "Instituto Quadrix"),
            "orgao": metadados.get("orgao"),
            "ano": metadados.get("ano"),
            "prova": metadados.get("prova"),
            "fonte": "quadrix_pdf",
        })
        resultado["salvas" if salvou else "duplicadas"] += 1
    return resultado


def main():
    if not PROVAS:
        print("A lista PROVAS está vazia. Abra coletor_quadrix.py e adicione as URLs"
              " das provas da Quadrix que você quer importar.")
        return
    con = db.conectar()
    linhas_relatorio = []
    for prova in PROVAS:
        print(f"— {prova['nome']} —")
        try:
            caminho_prova = baixar(prova["url_prova"], PASTA_PDFS / f"{prova['nome']}_prova.pdf")
            caminho_gab = baixar(prova["url_gabarito"], PASTA_PDFS / f"{prova['nome']}_gabarito.pdf")
        except requests.exceptions.RequestException as erro:
            print(f"  Não consegui baixar ({erro.__class__.__name__})."
                  " Confira sua internet ou a URL e tente de novo.")
            continue
        r = processar_prova(caminho_prova, caminho_gab, con, prova)
        print(f"  salvas={r['salvas']} duplicadas={r['duplicadas']}"
              f" puladas={len(r['puladas'])} sem_materia={r['sem_materia']}")
        if r["puladas"]:
            linhas_relatorio.append(f"{prova['nome']}: questões puladas {r['puladas']}")
        if r["sem_materia"]:
            linhas_relatorio.append(f"{prova['nome']}: {r['sem_materia']} questões sem matéria reconhecida")
    if linhas_relatorio:
        ARQUIVO_RELATORIO.write_text("\n".join(linhas_relatorio), encoding="utf-8")
        print(f"Relatório de problemas: {ARQUIVO_RELATORIO}")
    con.close()


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Sem internet ou site fora do ar. Tente de novo mais tarde.")
        sys.exit(1)
