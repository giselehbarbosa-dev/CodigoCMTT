@echo off
chcp 65001 > nul

REM ===============================================================
REM --- CÓDIGO ANTIGO (ATIVO) ---
REM ===============================================================
REM Entra na pasta do projeto
cd "C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"

REM Roda o script usando o Python do seu ambiente virtual
REM (Caminho atualizado para a pasta motores)
".venv\Scripts\python.exe" "motores\atualizar_cache_auto.py" >> "logs_atualizacao.txt" 2>&1

REM O comando abaixo faz o Windows ignorar tudo o que vem depois!
goto fim_do_arquivo


REM ===============================================================
REM --- CÓDIGO NOVO (DESATIVADO TEMPORARIAMENTE) ---
REM ===============================================================
echo ===============================================================
echo  🏛️  PIPELINE DE DADOS CMTT - EXECUCAO AUTOMATICA
echo ===============================================================

cd /d "%~dp0"
set PYTHON_EXE=".venv\Scripts\python.exe"

echo.
echo [1/5] FASE 0 - COLETANDO DADOS DO SITE (SCRAPING)...
%PYTHON_EXE% "coletores\coletor_atas.py"
%PYTHON_EXE% "coletores\coletor_excel.py"

echo.
echo [2/5] FASE PREPARACAO - CONSTRUINDO GABARITOS E CACHE...
%PYTHON_EXE% "construtores\construtor_ambiente.py"
%PYTHON_EXE% "construtores\construtor_conselheiros.py"
%PYTHON_EXE% "construtores\construtor_index.py"
%PYTHON_EXE% "construtores\construtor_cache.py"

echo.
echo [3/5] FASE DE MINERACAO - EXTRAINDO PRESENCAS (O CEREBRO)...
%PYTHON_EXE% "motores\motor_extracao.py"

echo.
echo [4/5] FASE DE MINERACAO - EXTRAINDO TEMAS E OSCS...
%PYTHON_EXE% "motores\motor_tematico.py"

echo.
echo [5/5] FASE DE ANALISE - GERANDO RELATORIOS E GRAFICOS...
%PYTHON_EXE% "analisadores\relatorio_cadeiras.py"
%PYTHON_EXE% "analisadores\relatorio_visitantes.py"
%PYTHON_EXE% "analisadores\exportador_bases_graficos.py"

echo.
echo ===============================================================
echo  ✅ PIPELINE CONCLUIDO COM SUCESSO!
echo ===============================================================
pause

:fim_do_arquivo