# 📚 Banco de Questões SEDES/DF

Sistema de geração de simulados para o concurso da Secretaria de Desenvolvimento Social do Distrito Federal (Cargo 202 - TDAS).

**Status:** ✅ Pronto para uso

---

## 🚀 Como Usar

### Opção 1: Local (Windows - Recomendado)

1. **Execute o script START.cmd:**
   ```cmd
   START.cmd
   ```

2. **Abra no navegador:**
   ```
   http://localhost:8000
   ```

**O que pode fazer:**
- Ver estatísticas por matéria
- Gerar simulados por matéria
- Gerar simulado geral (60 questões distribuídas)
- Baixar PDFs gerados
- Coletar questões novas (CLI do `scraper_qc.py` ou `coletor_quadrix.py`)
- Zerar histórico de questões usadas

---

### Opção 2: Docker (Sem coleta no container)

1. **Instale Docker Desktop:** https://www.docker.com/products/docker-desktop

2. **Execute o PowerShell script:**
   ```powershell
   .\START-DOCKER.ps1
   ```
   
   Ou manualmente:
   ```bash
   docker compose up --build
   ```

3. **Abra no navegador:**
   ```
   http://localhost:8000
   ```

**Diferença:** Docker desabilita a coleta de questões (COLETA_DISPONÍVEL=0). O banco de dados e PDFs persistem no host via bind mount.

---

## 📋 Estrutura

```
training/
├── banco_questoes/              # Sistema principal
│   ├── banco_de_questoes.db     # SQLite com 537 questões
│   ├── web/
│   │   └── index.html           # Dashboard (servido em /)
│   ├── simulados/
│   │   ├── gerar_simulado.py    # Motor PDF (duas colunas)
│   │   └── *.pdf                # Simulados gerados
│   ├── db.py                    # API do banco (statisticas, sorteio)
│   ├── edital.py                # Metadados: 8 matérias, pesos
│   ├── web_api.py               # FastAPI (7 rotas)
│   ├── scraper_qc.py            # Coleta de questões do QConcursos
│   ├── coletor_quadrix.py       # Coleta de questões de PDFs (download)
│   └── tests/                   # 55 testes (TDD)
├── Dockerfile                   # Imagem (sem Selenium/coleta)
├── docker-compose.yml           # Compose: 8000:8000, bind mount
├── START.cmd                    # Atalho para rodar local
├── START-DOCKER.ps1             # Atalho para rodar Docker
└── README.md                    # Este arquivo
```

---

## 🧪 Testes

```bash
cd banco_questoes
..\.venv\Scripts\python.exe -m pytest -v
```

Resultado: **55 testes verdes** (Fase 1 + Fase 2)

---

## 📊 Dados

**Banco de questões:** 537 questões de 7 matérias (coleta real do QConcursos, agost 2026)

| Matéria | Total | Inéditas | Status |
|---------|-------|----------|--------|
| Língua Portuguesa | 102 | 102 | ✅ |
| Conhecimentos do DF | 72 | 72 | ✅ |
| Direito Administrativo | 78 | 78 | ✅ |
| Direito Constitucional | 58 | 58 | ✅ |
| SUAS | 87 | 87 | ✅ |
| Atendimento/Arquivologia | 77 | 77 | ✅ |
| Recursos Materiais | 63 | 63 | ✅ |
| Programas e Benefícios | 0 | 0 | ⚠️ (sem questões no QC) |

---

## 🔧 API FastAPI

Todas as rotas seguem padrão REST em `/api/`:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/stats` | Estatísticas por matéria |
| GET | `/api/materias` | Lista de 8 matérias |
| POST | `/api/simulado/materia` | Gera simulado por matéria |
| POST | `/api/simulado/completo` | Gera simulado geral (distribuído) |
| GET | `/api/simulados/download/{nome}` | Download com proteção |
| POST | `/api/simulados/zerar` | Reseta histórico |
| POST | `/api/coletar` | Inicia coleta (503 em Docker) |

---

## 🎨 Tecnologia

**Backend:**
- Python 3.14 (venv)
- FastAPI + Uvicorn
- SQLite (banco_de_questoes.db)
- ReportLab (PDFs em duas colunas)
- Playwright + BeautifulSoup (Web scraping)

**Frontend:**
- HTML5 + CSS3 (responsivo)
- JavaScript vanilla (sem frameworks)
- Cores: #1B3A6B (azul SEDES)

**DevOps:**
- Docker + Docker Compose
- Bind mount de ./banco_questoes:/app

---

## 📝 Fase 1 (Concluída)

- ✅ Task 1: Setup + DB (schema, dedupe)
- ✅ Task 2: Sorteio + Gabarito  
- ✅ Task 3: Edital (matérias canonicas)
- ✅ Task 4: Motor PDF (duas colunas)
- ✅ Task 5: Parser de textos (QConcursos)
- ✅ Task 6: Processamento completo (download, relatório)
- ✅ Task 7: Fixture HTML + Parser de blocos
- ✅ Task 8: Navegação + Paginação (405 questões / 7 matérias)
- ✅ Task 9: Fase de gabaritos (seletores HTML)
- ✅ Task 10: Texto-base + Imagens
- ✅ Task 11: Formato de prova (duas colunas com cabeçalho)

## 📊 Fase 2 (Concluída)

- ✅ Task 1: Pesos + Distribuição + Estatísticas
- ✅ Task 2: Simulado Geral em PDF
- ✅ Task 3: API FastAPI (7 rotas)
- ✅ Task 4: Dashboard web (HTML+CSS+JS)
- ✅ Task 5: Docker + Compose

---

## 🐛 Conhecidos

- **Gabaritos:** 102/537 questões tem gabarito (coleta pendente)
- **Programas e Benefícios:** Sem questões no QConcursos (conteúdo exclusivo)
- **Docker:** Desabilita coleta no container (use CLI do host)

---

## 📧 Autor

Desenvolvido com Claude (TDD + Parallelização com Agentes).  
Fase 1 + 2: 11 tasks, 55 testes verdes, 0 bugs críticos.

---

**Última atualização:** 2026-08-13  
**Versão:** 2.0 (Fase 2 Completa)
