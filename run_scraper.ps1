# Script para rodar scraper e preencher o banco de questões

Write-Host "Iniciando Scraper de Questoes..." -ForegroundColor Green
Write-Host "=" * 60

# Ativa venv
Write-Host "Ativando ambiente virtual..."
& .\.venv\Scripts\Activate.ps1

# Define ambiente
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/banco_questoes"

# Roda scraper QConcursos
Write-Host "Rodando QConcursos Scraper..." -ForegroundColor Cyan
Write-Host "Isso pode levar alguns minutos..." -ForegroundColor Yellow

python -m banco_questoes.scraper_qc

Write-Host ""
Write-Host "Scraper Finalizado!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "Verificando questoes coletadas..." -ForegroundColor Cyan
Write-Host ""

# Chama script Python para verificar
python check_questoes.py

Write-Host ""
Write-Host "Pronto! Acesse http://localhost:8000" -ForegroundColor Green
Write-Host "   e escolha um cargo para gerar simulado!" -ForegroundColor Green
