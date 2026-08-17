#!/bin/bash
# Inicia o dashboard completo

echo "Iniciando Dashboard PCI..."
echo "================================================"

cd "$(dirname "$0")"

# Inicia FastAPI
echo "[1] Iniciando servidor FastAPI na porta 8000..."
python -m uvicorn banco_questoes.web_api:app --reload --host 0.0.0.0 --port 8000
