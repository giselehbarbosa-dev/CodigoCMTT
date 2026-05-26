import unicodedata
import re
import os
from dotenv import load_dotenv

# Carrega as variáveis do cofre (.env)
load_dotenv()

# ==============================================================================
# 0. CHAVE DE AMBIENTE (INTERRUPTOR DE TESTES)
# ==============================================================================
# Lê o .env. Se estiver "True", a variável MODO_TESTE vira um booleano Verdadeiro do Python.
MODO_TESTE = os.getenv("MODO_TESTE", "False").lower() in ("true", "1", "t", "yes", "y")

# ==============================================================================
# 1. RAIZ DO PROJETO E REDE (Auto-Detectável e Blindado)
# ==============================================================================
if MODO_TESTE:
    print("⚠️ ATENÇÃO: SISTEMA RODANDO EM MODO DE TESTE (SANDBOX) ⚠️")
    # Usa as pastas temporárias de Downloads (Não suja a base oficial)
    BASE_DIR = os.getenv("DIR_TESTE_LOCAL")
    DIR_REDE_INTERNA = os.getenv("DIR_TESTE_REDE")
else:
    # Usa as pastas reais (Produção)
    BASE_DIR = os.getenv("BASE_DIR_PROJETO")
    DIR_REDE_INTERNA = os.getenv("DIR_REDE_INTERNA")

# Se não achar o cofre (ex: rodando na nuvem do Streamlit), o sistema descobre a raiz sozinho!
if not BASE_DIR:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"⚠️ BASE_DIR não encontrado no .env. Auto-detectado: {BASE_DIR}")


# ==============================================================================
# 2. DIRETÓRIOS DE DADOS
# ==============================================================================
CAMINHO_DADOS = os.path.join(BASE_DIR, "dados")
CAMINHO_BASE_DADOS = os.path.join(CAMINHO_DADOS, "base_dados")
CAMINHO_CONFIGS = os.path.join(CAMINHO_DADOS, "configs")
CAMINHO_PROCESSADOS = os.path.join(CAMINHO_DADOS, "processados")

# ==============================================================================
# 3. DIRETÓRIOS DE OUTPUTS (Gráficos e Relatórios agora moram aqui)
# ==============================================================================
CAMINHO_OUTPUTS = os.path.join(BASE_DIR, "outputs")
CAMINHO_GRAFICOS = os.path.join(CAMINHO_OUTPUTS, "graficos")
CAMINHO_RELATORIOS = os.path.join(CAMINHO_OUTPUTS, "relatorios")

# ==============================================================================
# 4. CAMINHOS ESPECÍFICOS E GABARITOS
# ==============================================================================
CAMINHO_PDFS_PADRAO = os.path.join(CAMINHO_BASE_DADOS, "pdf_atas_pleno")
CAMINHO_INDEX_JSON = os.path.join(CAMINHO_CONFIGS, "index_atas.json")
CAMINHO_EXCEL_MANDATOS = os.path.join(CAMINHO_BASE_DADOS, "base_mandatosCMTT.xlsx")
CAMINHO_EXCEL_INDEX = os.path.join(CAMINHO_BASE_DADOS, "index_atasCMTT.xlsx")
CAMINHO_CACHE_BUSCADOR = os.path.join(CAMINHO_CONFIGS, ".cache_corpus_atas.json")

# ==============================================================================
# 5. ARQUIVOS PROCESSADOS (A Ponte entre a Fase 1 e as Fases seguintes)
# ==============================================================================
NOME_CSV_PRESENCA = "presenca_oficial.csv"
NOME_CSV_VISITANTES = "visitantes_geral.csv"
CAMINHO_CSV_PRESENCA = os.path.join(CAMINHO_PROCESSADOS, NOME_CSV_PRESENCA)
CAMINHO_CSV_VISITANTES = os.path.join(CAMINHO_PROCESSADOS, NOME_CSV_VISITANTES)

# ==============================================================================
# 6. RELATÓRIOS E BASES EXCEL (Saídas Finais)
# ==============================================================================
NOME_EXCEL_GRAFICOS = "Base_Para_Graficos_CMTT.xlsx"
NOME_EXCEL_VISITANTES = "Relatorio_Visitantes_Lobby.xlsx"
NOME_EXCEL_CADEIRAS = "Relatorio_Cadeiras_V8.xlsx"
NOME_EXCEL_DICIONARIO = "Catálogo_de_Metadados_CMTT.xlsx"
CAMINHO_EXCEL_GRAFICOS = os.path.join(CAMINHO_GRAFICOS, NOME_EXCEL_GRAFICOS)
CAMINHO_EXCEL_VISITANTES = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_VISITANTES)
CAMINHO_EXCEL_CADEIRAS = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_CADEIRAS)
CAMINHO_EXCEL_DICIONARIO = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_DICIONARIO)

# ==============================================================================
# 7. ARQUIVOS ESTÁTICOS E TEMPORÁRIOS (Logos e Buscas)
# ==============================================================================
NOME_LOGO1 = "logo_prefeitura.png"
NOME_LOGO2 = "logo_cmtt.jpg"
NOME_EXCEL_BUSCA = "ultimo_resultado_busca.xlsx"
CAMINHO_LOGO1 = os.path.join(CAMINHO_CONFIGS, NOME_LOGO1)
CAMINHO_LOGO2 = os.path.join(CAMINHO_CONFIGS, NOME_LOGO2)
CAMINHO_EXCEL_BUSCA = os.path.join(CAMINHO_RELATORIOS, NOME_EXCEL_BUSCA)

# ==============================================================================
# 8. VARIÁVEIS DE NUVEM E SEGURANÇA (GitHub e App)
# ==============================================================================
SENHA_ADMIN = os.getenv("SENHA_ADMIN_APP", "admin123")
GITHUB_USER = os.getenv("GITHUB_USUARIO", "giselehbarbosa-dev")
GITHUB_REPO = os.getenv("GITHUB_REPO", "CodigoCMTT")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# ==============================================================================
# 9. ARQUITETURA WHITE-LABEL E REGRAS DE NEGÓCIO (FONTE DA VERDADE)
# ==============================================================================

REGRAS_CONSELHO = {
    "sigla": "CMTT",
    "url_base_site": "https://prefeitura.sp.gov.br/mobilidade/w/participacao_social/215759",

    "termo_reuniao_extra": r"Extraordinária",
    "regex_arquivo_extra": r"extra_(\d+)",
    "label_auditoria_ia": "Possível Conselheiro",

    "colunas_excel_index": [
        "Órgão", "Nome da Reunião", "Data", "Horário",
        "Local", "Link Reunião (Online)", "Ata"
    ],
    "orgaos_palavras_chave": {
        "Conselho Pleno": [r"pleno", r"cmtt"],
        "Câmara Temática de Mobilidade a Pé": [r"mobilidade\s*a\s*p[eé]"],
        "Câmara Temática de Bicicleta": [r"bicicleta"],
        "Câmara Temática de Motocicleta": [r"motocicleta"],
        "Câmara Temática de Táxi": [r"t[aá]xi"],
        "Câmara Temática de Transporte Escolar": [r"transporte\s*escolar"]
    },
    "tipos_reuniao": {
        "Reunião Extraordinária": [r"extraordin[aá]ria"],
        "Reunião Técnica": [r"t[eé]cnica"],
        "Reunião Ordinária": [r"ordin[aá]ria", r"reuni[aã]o"]
    },
    "identificadores_links": {
        "Link Reunião (Online)": [r"teams\.microsoft", r"zoom", r"meet"],
        "Apresentacoes": [r"apresentaç", r"apresentac"],
        "Ata": [r"ata"]
    },
    "palavras_navegacao_subpaginas": [r"c[aâ]mara\s*tem[aá]tica"],

    # 🆕 CÉREBRO TEMÁTICO V3 - Desmembrado (12 Categorias Espelhadas na Realidade Institucional)
    "dicionario_temas": {
        "Composição e Governança do Conselho": [
            r"conselho", r"conselheiro", r"eleic", r"mandato", r"regimento interno", r"posse", r"representante"
        ],
        "Estrutura e Organização da Rede Viária": [
            r"via\b", r"corredor", r"semaforo", r"asfalto", r"faixa exclusiva", r"recapeamento", r"rodizio", r"engenharia de trafego", r"cet\b"
        ],
        "Mobilidade Urbana: Organização Geral e Prestação de Contas": [
            r"tarifa", r"orcament", r"custos", r"plano de mobilidade", r"planmob", r"subsidio", r"plano diretor", r"prestacao de contas"
        ],
        "Segurança Viária": [
            r"seguranca", r"acidente", r"velocidade", r"morte", r"atropelamento", r"sinistro", r"visao zero"
        ],
        "Logística Urbana e Transporte de Cargas": [
            r"carga", r"logistica", r"caminhao", r"vuc\b", r"restricao", r"fretamento de carga"
        ],
        "Transporte Público Coletivo": [
            r"onibus", r"sptrans", r"transporte coletivo", r"frota", r"emtu", r"metro\b", r"terminal", r"bilhete unico"
        ],
        "Transporte Escolar e Fretamento": [
            r"escolar", r"teg\b", r"van\b", r"fretamento", r"fretado"
        ],
        "Motocicletas e Motofrete": [
            r"moto", r"entregador", r"motofrete", r"faixa azul"
        ],
        "Mobilidade Ativa: Bicicletas": [
            r"ciclovia", r"ciclofaixa", r"cicloativismo", r"bicicleta", r"bike", r"ciclista"
        ],
        "Mobilidade Ativa: Acessibilidade e Pedestres": [
            r"pedestre", r"calcada", r"acessibilidade", r"cadeirante", r"travessia", r"piso tátil"
        ],
        "Transporte Individual: Táxis": [
            r"taxi\b", r"taxista", r"alvara", r"dtp\b", r"ponto de taxi"
        ],
        "Transporte Individual: Aplicativos": [
            r"aplicativo", r"uber\b", r"99\b", r"app\b", r"transporte por aplicativo"
        ]
    }
}

URL_BASE_SITE = os.getenv("URL_BASE_SITE", REGRAS_CONSELHO["url_base_site"])
COLUNAS_INDEX_BASE = REGRAS_CONSELHO["colunas_excel_index"]
MAPA_ORGAOS_TERMOS = REGRAS_CONSELHO["orgaos_palavras_chave"]
DICIONARIO_TEMAS = REGRAS_CONSELHO["dicionario_temas"]

# ==========================================
# 🎨 DICIONÁRIO VISUAL (DE/PARA DA NUVEM DE PALAVRAS)
# ==========================================
MAPA_PALAVRAS_BONITAS = {
    "eleic": "Eleição", "orcament": "Orçamento", "semaforo": "Semáforo",
    "calcada": "Calçada", "onibus": "Ônibus", "caminhao": "Caminhão",
    "logistica": "Logística", "visao zero": "Visão Zero", "sptrans": "SPTrans",
    "emtu": "EMTU", "dtp": "DTP", "cet": "CET", "teg": "TEG", "vuc": "VUC",
    "regimento interno": "Regimento Interno", "plano diretor": "Plano Diretor",
    "plano de mobilidade": "Plano de Mobilidade", "planmob": "PlanMob",
    "acessibilidade": "Acessibilidade", "seguranca": "Segurança",
    "veiculo": "Veículo", "pedestre": "Pedestre", "faixa azul": "Faixa Azul",
    "bilhete unico": "Bilhete Único", "transporte coletivo": "Transporte Coletivo",
    "engenharia de trafego": "Engenharia de Tráfego", "prestacao de contas": "Prestação de Contas",
    "fretamento de carga": "Fretamento de Carga", "transporte por aplicativo": "Aplicativos de Mobilidade"
}

# GERAÇÃO DINÂMICA DE CAMINHOS
MAPA_REDE_INTERNA = {}
if DIR_REDE_INTERNA:
    for orgao in MAPA_ORGAOS_TERMOS.keys():
        nome_limpo = ''.join(c for c in unicodedata.normalize('NFD', orgao) if unicodedata.category(c) != 'Mn')
        nome_pasta = re.sub(r'Camara_Tematica_(de_)?', 'CT_', nome_limpo.replace(" ", "_"), flags=re.IGNORECASE)
        MAPA_REDE_INTERNA[orgao] = os.path.join(DIR_REDE_INTERNA, nome_pasta)

# Mapeamento de Macro Forças
MAPA_MACRO_FORCAS = {
    "Poder Público": ["ÓRGÃO", "PÚBLICO", "MUNICIPAL", "SECRETARIA", "ESTADUAL"],
    "Operadores": ["OPERADORES", "SETOR EMPRESARIAL", "SINDICATO", "EMPRESA"],
    "Sociedade Civil": ["SOCIEDADE CIVIL", "ONG", "ASSOCIAÇÃO", "COLETIVO", "MOVIMENTO"]
}