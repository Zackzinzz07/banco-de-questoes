@echo off
REM Script para iniciar o banco de questoes
cd /d "%~dp0"

echo.
echo ========================================
echo Banco de Questoes SEDES/DF
echo ========================================
echo.
echo Iniciando API em http://localhost:8000
echo.

REM Verificar se venv existe
if not exist ".venv" (
    echo Erro: .venv nao encontrado. Execute:
    echo   python -m venv .venv
    pause
    exit /b 1
)

REM Ativar venv e rodar uvicorn
cd banco_questoes
call ..\.venv\Scripts\activate.bat
python -m uvicorn web_api:app --host 0.0.0.0 --port 8000 --reload
