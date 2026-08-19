# PCI Concursos - Coleta Hierárquica

Coleta automática de questões do PCI Concursos, organizadas por **Matéria → Categoria → Tema**.

**Status:** Rodando - 19.721+ questões

---

## Setup (5 min)

### 1. Ambiente Virtual
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Banco de Dados (Docker)
```bash
docker-compose up -d
sleep 10
```

### 3. Rodar Coleta
```bash
python run_pci.py
```

Monitor em outro terminal:
```bash
python monitorar_pci.py
```

### 4. API Web (opcional)
```bash
python -m uvicorn banco_questoes.web_api:app --host 0.0.0.0 --port 8000 --reload
```

Acesso: http://localhost:8000

---

## Estrutura

```
├── banco_questoes/
│   ├── db.py                      # Banco PostgreSQL
│   ├── web_api.py                 # API FastAPI
│   ├── conteudo_mapper.py         # Mapeamento matéria/categoria/tema
│   ├── mapeamento_conteudos.yaml  # Configuração
│   ├── scrapers/
│   │   └── pci/
│   │       ├── coletor_v2.py      # Coleta (MAIN)
│   │       └── parser.py          # Parse HTML
│   └── web/
│       └── dashboard_pci.html     # Dashboard
│
├── run_pci.py                     # Iniciar coleta
├── monitorar_pci.py               # Monitor progresso
├── requirements.txt               # Dependências
└── docker-compose.yml             # PostgreSQL
```

---

## Dados

**19.721+ questões** do PCI Concursos:

| Nível | Quantidade |
|-------|-----------|
| Matérias | 12+ |
| Categorias | 22+ |
| Temas | 150+ |
| Questões | 19.721+ |
| Com Imagens | ~40% |

**Salvos com:**
- `enunciado` - Pergunta
- `alternativas` - JSON {A, B, C, D, E}
- `gabarito` - Resposta correta
- `materia`, `categoria`, `tema` - Hierarquia
- `imagens_urls` - URLs das imagens
- `ano` - Ano da prova

---

## Coleta

**Hierárquica em 3 níveis:**

1. Matéria (ex: Saúde)
2. Categoria (ex: Farmacologia)
3. Tema (ex: Medicamentos)

**Taxa:** ~1.5K questões/minuto

**Resumível:** Interrompe e retoma automaticamente via checkpoints

---

## API Endpoints

```
GET  /api/stats              → Estatísticas totais
GET  /api/stats/materias     → Por matéria
GET  /api/stats/pci          → Hierarquia PCI (cat/tema)
GET  /api/stats/pci/{cat}    → Temas de uma categoria
```

---

## Banco de Dados

PostgreSQL (Docker):
```
Host: localhost
Port: 5432
Database: banco_questoes
User: postgres
Password: postgres
```

**Tabelas:**
- `questoes` - Questões (19K+)
- `progresso_scraper` - Checkpoints

---

**Versão:** 3.0  
**Foco:** PCI Concursos (Matéria/Categoria/Tema)  
**Última atualização:** 2026-08-18
