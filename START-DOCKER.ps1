#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Inicia o banco de questões via Docker Compose
.DESCRIPTION
  Este script verifica se Docker está rodando e inicia o banco de questões
#>

Write-Host ""
Write-Host "========================================"
Write-Host "Banco de Questoes SEDES/DF - Docker"
Write-Host "========================================"
Write-Host ""

# Verificar Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✓ Docker: $dockerVersion"
} catch {
    Write-Host "✗ Docker não está instalado ou não está rodando"
    Write-Host "   Instale Docker Desktop de: https://www.docker.com/products/docker-desktop"
    Write-Host ""
    Read-Host "Pressione ENTER para sair"
    exit 1
}

Write-Host ""
Write-Host "Iniciando containers..."
Write-Host "Acesse: http://localhost:8000"
Write-Host ""
Write-Host "Para parar, pressione CTRL+C"
Write-Host ""

# Executar docker compose up
docker compose up --build
