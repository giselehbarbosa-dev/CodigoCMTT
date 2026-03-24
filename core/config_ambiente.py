import os
from dotenv import load_dotenv

# Carrega as variáveis do cofre (.env)
load_dotenv()

# 1. RAIZ DO PROJETO (Auto-Detectável)
BASE_DIR = os.getenv("BASE_DIR_PROJETO")

# Se não achar o cofre (ex: rodando na nuvem do Streamlit), o sistema descobre a raiz sozinho!
if not BASE_DIR:
    # O config_ambiente.py está na pasta 'core'. O "pai" dela ('..') é a raiz do projeto.
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"⚠️ BASE_DIR_PROJETO não encontrado no .env. Auto-detectado: {BASE_DIR}")

DIR_REDE_INTERNA = os.getenv("DIR_REDE_INTERNA") # (Opcional)

# 2. DIRETÓRIOS DE DADOS
CAMINHO_DADOS = os.path.join(BASE_DIR, "dados")
CAMINHO_BASE_DADOS = os.path.join(CAMINHO_DADOS, "base_dados")
CAMINHO_CONFIGS = os.path.join(CAMINHO_DADOS, "configs")
CAMINHO_PROCESSADOS = os.path.join(CAMINHO_DADOS, "processados")

# 3. DIRETÓRIOS DE OUTPUTS (Gráficos e Relatórios agora moram aqui)
CAMINHO_OUTPUTS = os.path.join(BASE_DIR, "outputs")
CAMINHO_GRAFICOS = os.path.join(CAMINHO_OUTPUTS, "graficos")
CAMINHO_RELATORIOS = os.path.join(CAMINHO_OUTPUTS, "relatorios")

# 4. CAMINHOS ESPECÍFICOS E GABARITOS
CAMINHO_PDFS_PADRAO = os.path.join(CAMINHO_BASE_DADOS, "pdf_atas_pleno")
CAMINHO_INDEX_JSON = os.path.join(CAMINHO_CONFIGS, "index_atas.json")
CAMINHO_EXCEL_MANDATOS = os.path.join(CAMINHO_BASE_DADOS, "base_mandatosCMTT.xlsx")
CAMINHO_EXCEL_INDEX = os.path.join(CAMINHO_BASE_DADOS, "index_atasCMTT.xlsx")
CAMINHO_CACHE_BUSCADOR = os.path.join(CAMINHO_CONFIGS, ".cache_corpus_atas.json")

# 5. ARQUIVOS PROCESSADOS (A Ponte entre a Fase 1 e as Fases seguintes)
NOME_CSV_PRESENCA = "presenca_oficial.csv"
NOME_CSV_VISITANTES = "visitantes_geral.csv"
CAMINHO_CSV_PRESENCA = os.path.join(CAMINHO_PROCESSADOS, NOME_CSV_PRESENCA)
CAMINHO_CSV_VISITANTES = os.path.join(CAMINHO_PROCESSADOS, NOME_CSV_VISITANTES)

# 6. RELATÓRIOS E BASES EXCEL (Saídas Finais)
NOME_EXCEL_GRAFICOS = "Base_Para_Graficos_CMTT.xlsx"
NOME_EXCEL_VISITANTES = "Relatorio_Visitantes_Lobby.xlsx"
NOME_EXCEL_CADEIRAS = "Relatorio_Cadeiras_Absenteismo.xlsx"
CAMINHO_EXCEL_GRAFICOS = os.path.join(CAMINHO_GRAFICOS, NOME_EXCEL_GRAFICOS)
CAMINHO_EXCEL_VISITANTES = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_VISITANTES)
CAMINHO_EXCEL_CADEIRAS = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_CADEIRAS)

# 7. ARQUIVOS ESTÁTICOS E TEMPORÁRIOS (Logos e Buscas)
NOME_LOGO1 = "logo_prefeitura.png"
NOME_LOGO2 = "logo_cmtt.jpg"
# NOME_LOGO3 = "outro_logo.png"  <-- Exemplo: você pode adicionar quantos quiser no futuro!
NOME_EXCEL_BUSCA = "ultimo_resultado_busca.xlsx"
CAMINHO_LOGO1 = os.path.join(CAMINHO_CONFIGS, NOME_LOGO1)
CAMINHO_LOGO2 = os.path.join(CAMINHO_CONFIGS, NOME_LOGO2)
CAMINHO_EXCEL_BUSCA = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_BUSCA)

# 8. VARIÁVEIS DE NUVEM E SEGURANÇA (GitHub e App)
SENHA_ADMIN = os.getenv("SENHA_ADMIN_APP", "admin123") # admin123 é o fallback caso esqueçam o .env
GITHUB_USER = os.getenv("GITHUB_USUARIO", "giselehbarbosa-dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "CodigoCMTT")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")