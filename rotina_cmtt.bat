@echo off
REM Entra na pasta do projeto
cd "C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"

REM Roda o script usando o Python do seu ambiente virtual
".venv\Scripts\python.exe" "analisadores\atualizar_cache_auto.py" >> "logs_atualizacao.txt" 2>&1