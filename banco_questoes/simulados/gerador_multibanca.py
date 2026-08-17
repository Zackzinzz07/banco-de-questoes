"""Motor principal multi-banca: gera simulados em PDF respeitando o layout e o
estilo visual de cada banca examinadora (Cebraspe, IADES, Quadrix, FGV, AOCP).

Diferente de `gerar_simulado.py` (que usa flowables do ReportLab com um único
layout fixo no estilo Quadrix), este módulo desenha diretamente no Canvas do
ReportLab, delegando cabeçalho/rodapé/questão/altura para uma subclasse de
`BaseBancaStyle` (ver `simulados.estilos`), permitindo paginação automática
com detecção de altura por banca.

As 5 bancas em BANCAS (cebraspe, iades, quadrix, fgv, aocp) têm cada uma sua
classe de estilo concreta em `simulados.estilos.<banca>` (Tasks 2-4). Caso uma
classe de estilo esteja ausente (regressão ou banca nova ainda não
implementada), `_carregar_estilo()` levanta NotImplementedError de forma
explícita em vez de falhar silenciosamente.
"""
import importlib
import io
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as reportlab_canvas

import db

PASTA_CONFIGS = Path(__file__).resolve().parent.parent / "configuracoes_bancas"
PASTA_SAIDA = Path(__file__).resolve().parent

W, H = A4

# Espaço vertical entre questões consecutivas na mesma coluna.
ESPACO_ENTRE_QUESTOES_PT = 8

# Largura da calha (gutter) entre colunas.
CALHA_CM = 0.4


# Registro central das 5 bancas suportadas: arquivo YAML (Task 1), módulo e
# classe de estilo (Task 2 = base; Tasks 3/4 = implementações concretas).
BANCAS: Dict[str, Dict[str, str]] = {
    "cebraspe": {"yaml": "cebraspe.yaml", "modulo": "cebraspe", "classe": "EstiloCebraspe"},
    "iades": {"yaml": "iades.yaml", "modulo": "iades", "classe": "EstiloIADES"},
    "quadrix": {"yaml": "quadrix.yaml", "modulo": "quadrix", "classe": "EstiloQuadrix"},
    "fgv": {"yaml": "fgv.yaml", "modulo": "fgv", "classe": "EstiloFGV"},
    "aocp": {"yaml": "aocp.yaml", "modulo": "aocp", "classe": "EstiloAOCP"},
}


class GeradorSimuladoMultiBanca:
    """Motor de geração de simulados em PDF para múltiplas bancas examinadoras.

    Uso:
        >>> gerador = GeradorSimuladoMultiBanca("cebraspe")
        >>> caminho = gerador.gerar(quantidade=10, simulado_nome="teste_cebraspe")
    """

    def __init__(self, banca_nome: str, con=None) -> None:
        """
        Args:
            banca_nome: Chave da banca em BANCAS (ex: "cebraspe", "iades",
                "quadrix", "fgv", "aocp").
            con: Conexão já aberta com o banco (ver `db.conectar()`). Se None,
                uma conexão própria é aberta em `gerar()` e fechada ao final.

        Raises:
            ValueError: Se banca_nome não estiver em BANCAS.
        """
        if banca_nome not in BANCAS:
            disponiveis = ", ".join(sorted(BANCAS))
            raise ValueError(
                f"Banca '{banca_nome}' desconhecida. Bancas disponíveis: {disponiveis}"
            )

        self.banca_nome = banca_nome
        self.con = con

        self.config = self._carregar_config()
        self.estilo = self._carregar_estilo()

    # ------------------------------------------------------------------
    # Carregamento de configuração e estilo
    # ------------------------------------------------------------------

    def _carregar_config(self) -> Dict[str, Any]:
        """Carrega e retorna o dicionário de configuração da banca a partir do
        YAML correspondente em `configuracoes_bancas/` (Task 1).

        O YAML tem um único nó de topo (nem sempre igual à chave em BANCAS,
        ex: aocp.yaml usa "instituto_aocp"); por isso extraímos o primeiro
        (e único) valor do dicionário top-level em vez de indexar por nome.

        Returns:
            Dict[str, Any]: configuração no formato esperado por
            `BaseBancaStyle.__init__` (estilo_visual, caracteristicas_prova,
            estrutura_disciplinas_padrao).

        Raises:
            FileNotFoundError: se o YAML da banca não existir.
        """
        info = BANCAS[self.banca_nome]
        caminho = PASTA_CONFIGS / info["yaml"]
        if not caminho.exists():
            raise FileNotFoundError(f"Configuração YAML não encontrada: {caminho}")

        with open(caminho, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if not dados:
            raise ValueError(f"YAML vazio ou inválido: {caminho}")

        # Preferir a chave com o nome exato da banca; caso não exista
        # (inconsistência de nomenclatura, ex: aocp.yaml -> "instituto_aocp"),
        # usar o único valor de topo disponível.
        if self.banca_nome in dados:
            return dados[self.banca_nome]
        return next(iter(dados.values()))

    def _carregar_estilo(self):
        """Importa dinamicamente `simulados.estilos.<modulo>` e instancia a
        classe de estilo concreta (subclasse de BaseBancaStyle) para a banca.

        Raises:
            NotImplementedError: se o módulo/classe de estilo da banca ainda
                não existir (bancas cujas Tasks 3/4 não foram concluídas).
        """
        info = BANCAS[self.banca_nome]
        modulo_nome = f"simulados.estilos.{info['modulo']}"
        try:
            modulo = importlib.import_module(modulo_nome)
        except ImportError as erro:
            raise NotImplementedError(
                f"Estilo da banca '{self.banca_nome}' ainda não implementado "
                f"(módulo '{modulo_nome}' não encontrado; depende das Tasks 3/4 "
                f"do plano multi-banca-simulado). Erro original: {erro}"
            ) from erro

        classe = getattr(modulo, info["classe"], None)
        if classe is None:
            raise NotImplementedError(
                f"Classe '{info['classe']}' não encontrada em '{modulo_nome}' "
                f"para a banca '{self.banca_nome}'."
            )
        return classe(self.config)

    # ------------------------------------------------------------------
    # Busca de questões no banco
    # ------------------------------------------------------------------

    def _buscar_questoes(self, con, quantidade: int) -> List[Dict[str, Any]]:
        """Busca `quantidade` questões no banco, distribuindo a busca pelas
        disciplinas padrão da banca (estrutura_disciplinas_padrao) na
        proporção de peso configurada em cada disciplina, com fallback
        genérico (qualquer matéria) para completar o que faltar.

        Args:
            con: Conexão com o banco (db.conectar()).
            quantidade: Número total de questões desejado.

        Returns:
            List[Dict[str, Any]]: questões (mesmo formato de
            `db.sortear_questoes`), com no máximo `quantidade` itens
            (podendo ser menos se o banco não tiver questões suficientes).
        """
        disciplinas = self.config.get("estrutura_disciplinas_padrao", [])
        questoes: List[Dict[str, Any]] = []
        ids_vistos = set()

        if disciplinas:
            peso_total = sum(d.get("quantidade_questoes", 0) for d in disciplinas) or 1
            for disciplina in disciplinas:
                peso = disciplina.get("quantidade_questoes", 0)
                n_disciplina = round(quantidade * peso / peso_total)
                if n_disciplina <= 0:
                    continue
                materia = disciplina.get("nome", "")
                encontradas = db.sortear_questoes(con, materia, n_disciplina)
                for q in encontradas:
                    if q["id"] not in ids_vistos:
                        ids_vistos.add(q["id"])
                        questoes.append(q)

        # Backfill genérico: completa o déficit com questões de qualquer
        # matéria (necessário porque os nomes de disciplina da banca nem
        # sempre batem exatamente com `questoes.materia` no banco).
        faltam = quantidade - len(questoes)
        if faltam > 0:
            genericas = self._sortear_generico(con, faltam, excluir_ids=ids_vistos)
            questoes.extend(genericas)

        return questoes[:quantidade]

    def _sortear_generico(self, con, quantidade: int, excluir_ids=None) -> List[Dict[str, Any]]:
        """Sorteia questões de qualquer matéria (ineditas primeiro, repetidas
        para completar), ignorando ids já selecionados. Usado como fallback
        de `_buscar_questoes` quando a distribuição por disciplina não é
        suficiente.
        """
        import json

        excluir_ids = excluir_ids or set()
        linhas = con.execute(
            "SELECT * FROM questoes WHERE usada_em_simulado=0 ORDER BY RANDOM() LIMIT %s",
            (quantidade + len(excluir_ids),),
        ).fetchall()
        candidatas = [dict(l) for l in linhas if dict(l)["id"] not in excluir_ids][:quantidade]

        faltam = quantidade - len(candidatas)
        if faltam > 0:
            linhas_rep = con.execute(
                "SELECT * FROM questoes WHERE usada_em_simulado=1 ORDER BY RANDOM() LIMIT %s",
                (faltam + len(excluir_ids),),
            ).fetchall()
            repetidas = [dict(l) for l in linhas_rep if dict(l)["id"] not in excluir_ids][:faltam]
            candidatas.extend(repetidas)

        for q in candidatas:
            if isinstance(q.get("alternativas"), str):
                q["alternativas"] = json.loads(q["alternativas"])
            if isinstance(q.get("imagens"), str) and q["imagens"]:
                q["imagens"] = json.loads(q["imagens"])
            elif not q.get("imagens"):
                q["imagens"] = []
        return candidatas

    # ------------------------------------------------------------------
    # Preparação de dados de questão para o estilo
    # ------------------------------------------------------------------

    def _preparar_questao_data(self, numero: int, q: Dict[str, Any]) -> Dict[str, Any]:
        """Converte uma linha de `questoes` (formato do banco) no dicionário
        `questao_data` esperado pela interface de `BaseBancaStyle`
        (numero, enunciado, opcoes, tipo).
        """
        alternativas = q.get("alternativas") or {}
        opcoes = [
            {"letra": letra, "texto": texto}
            for letra, texto in sorted(alternativas.items())
        ]
        tipo = self.config.get("caracteristicas_prova", {}).get(
            "tipo_predominante", "Múltipla Escolha"
        )
        return {
            "numero": numero,
            "enunciado": q.get("enunciado", ""),
            "opcoes": opcoes,
            "tipo": tipo,
            "gabarito": q.get("gabarito"),
            "comentario": q.get("comentario"),
        }

    # ------------------------------------------------------------------
    # Geometria de página / paginação
    # ------------------------------------------------------------------

    def _layout_pagina(self, canvas_obj, pagina_numero: int) -> Tuple[float, float, float, List[float]]:
        """Desenha cabeçalho e rodapé da página atual e calcula a geometria
        de colunas disponível para as questões.

        Returns:
            Tuple(y_topo, y_fundo, largura_coluna, x_colunas): posições em
            pontos ReportLab prontas para o preenchimento das questões.
        """
        margens = self.estilo.obter_margens_pontos()
        altura_cabecalho = self.estilo.desenhar_cabecalho(canvas_obj, pagina_numero, W, H)
        altura_rodape = self.estilo.desenhar_rodape(canvas_obj, pagina_numero, W, H)

        y_topo = H - margens["superior"] - altura_cabecalho
        y_fundo = margens["inferior"] + altura_rodape
        largura_util = W - margens["esquerda"] - margens["direita"]

        colunas = int(self.estilo.estilo_visual.get("layout_colunas", 2)) or 1
        colunas = max(1, colunas)
        calha_pt = self.estilo.cm_para_pontos(CALHA_CM) if colunas > 1 else 0.0
        largura_coluna = (largura_util - calha_pt * (colunas - 1)) / colunas
        x_colunas = [
            margens["esquerda"] + i * (largura_coluna + calha_pt) for i in range(colunas)
        ]

        return y_topo, y_fundo, largura_coluna, x_colunas

    def _estimar_paginas(self, questoes: List[Dict[str, Any]]) -> int:
        """Estima o número total de páginas necessárias para renderizar
        `questoes`, sem desenhar nada em um PDF real (usa um canvas
        descartável em memória apenas para medir cabeçalho/rodapé).

        Args:
            questoes: lista de questões (formato do banco, já buscadas).

        Returns:
            int: número estimado de páginas (mínimo 1).
        """
        if not questoes:
            return 1

        buffer_descartavel = io.BytesIO()
        canvas_medicao = reportlab_canvas.Canvas(buffer_descartavel, pagesize=A4)

        pagina_numero = 1
        y_topo, y_fundo, largura_coluna, x_colunas = self._layout_pagina(
            canvas_medicao, pagina_numero
        )
        colunas = len(x_colunas)
        col_idx = 0
        y_cursor = y_topo

        for numero, q in enumerate(questoes, 1):
            questao_data = self._preparar_questao_data(numero, q)
            altura_necessaria = self.estilo.calcular_altura_questao(questao_data, largura_coluna)

            if y_cursor - altura_necessaria < y_fundo:
                col_idx += 1
                if col_idx >= colunas:
                    pagina_numero += 1
                    col_idx = 0
                y_cursor = y_topo

            y_cursor -= altura_necessaria + ESPACO_ENTRE_QUESTOES_PT

        return pagina_numero

    # ------------------------------------------------------------------
    # Renderização do PDF
    # ------------------------------------------------------------------

    def _renderizar_pdf(self, questoes: List[Dict[str, Any]], caminho_saida: Path) -> Path:
        """Desenha `questoes` em um PDF no caminho `caminho_saida`, usando o
        cabeçalho/rodapé/questão do estilo da banca, com paginação e quebra
        de coluna automáticas baseadas na altura calculada de cada questão.

        Args:
            questoes: lista de questões (formato do banco).
            caminho_saida: caminho completo (Path) do PDF a ser gerado.

        Returns:
            Path: o mesmo `caminho_saida`, após o PDF ter sido escrito em disco.
        """
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        c = reportlab_canvas.Canvas(str(caminho_saida), pagesize=A4)
        c.setTitle(f"Simulado {self.estilo.nome_oficial}")

        pagina_numero = 1
        y_topo, y_fundo, largura_coluna, x_colunas = self._layout_pagina(c, pagina_numero)
        colunas = len(x_colunas)
        col_idx = 0
        y_cursor = y_topo

        for numero, q in enumerate(questoes, 1):
            questao_data = self._preparar_questao_data(numero, q)
            altura_necessaria = self.estilo.calcular_altura_questao(questao_data, largura_coluna)

            if y_cursor - altura_necessaria < y_fundo:
                col_idx += 1
                if col_idx >= colunas:
                    c.showPage()
                    pagina_numero += 1
                    y_topo, y_fundo, largura_coluna, x_colunas = self._layout_pagina(
                        c, pagina_numero
                    )
                    col_idx = 0
                y_cursor = y_topo

            altura_usada = self.estilo.desenhar_questao(
                c, questao_data, x_colunas[col_idx], y_cursor, largura_coluna
            )
            y_cursor -= altura_usada + ESPACO_ENTRE_QUESTOES_PT

        c.save()
        return caminho_saida

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def gerar(self, quantidade: int, simulado_nome: str) -> str:
        """Gera um simulado em PDF no estilo desta banca.

        Args:
            quantidade: Número de questões a incluir no simulado.
            simulado_nome: Nome base do arquivo de saída (sem extensão) ou
                caminho completo (se contiver ".pdf" ou separador de path,
                é usado como está; caso contrário, o PDF é salvo em
                `simulados/<simulado_nome>.pdf`).

        Returns:
            str: caminho absoluto do PDF gerado.

        Raises:
            ValueError: se `quantidade` não for um inteiro positivo.
            RuntimeError: se não houver nenhuma questão disponível no banco.
        """
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError(f"quantidade deve ser um inteiro positivo, recebido: {quantidade}")

        con_proprio = self.con is None
        con = self.con if self.con is not None else db.conectar()

        try:
            questoes = self._buscar_questoes(con, quantidade)
            if not questoes:
                raise RuntimeError(
                    "Nenhuma questão disponível no banco para gerar o simulado "
                    f"da banca '{self.banca_nome}'. Rode os coletores primeiro."
                )

            total_paginas_estimado = self._estimar_paginas(questoes)
            print(
                f"Gerando simulado '{simulado_nome}' ({self.banca_nome}): "
                f"{len(questoes)} questões, ~{total_paginas_estimado} página(s) estimada(s)."
            )

            nome_str = str(simulado_nome)
            if nome_str.lower().endswith(".pdf") or "/" in nome_str or "\\" in nome_str:
                caminho_saida = Path(nome_str)
            else:
                caminho_saida = (
                    PASTA_SAIDA / f"{nome_str}_{self.banca_nome}_{date.today():%Y%m%d}.pdf"
                )

            caminho_final = self._renderizar_pdf(questoes, caminho_saida)

            ids = [q["id"] for q in questoes if q.get("id") is not None]
            if ids:
                db.marcar_usadas(con, ids)

            print(f"Simulado gerado: {caminho_final} ({len(questoes)} questões)")
            return str(caminho_final.resolve())
        finally:
            if con_proprio:
                con.close()
