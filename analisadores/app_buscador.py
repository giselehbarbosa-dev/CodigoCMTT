import sys
import os
import re
import json
import shutil
import base64
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud

# Configura o Plotly para Português (Brasil)
pio.templates.default = "plotly_white"

# Garantir caminhos do core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas
from construtores.construtor_cache import construir_cache_novo

CAMINHO_CACHE = config_ambiente.CAMINHO_CACHE_BUSCADOR
CAMINHO_BASE_MANDATOS = config_ambiente.CAMINHO_EXCEL_MANDATOS
CAMINHO_INDEX_EXCEL = config_ambiente.CAMINHO_EXCEL_INDEX
CAMINHO_RELATORIO_CADEIRAS = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "Relatorio_Cadeiras_Absenteismo.xlsx")

# --- Configuração da Página ---
sigla_conselho = config_ambiente.REGRAS_CONSELHO.get("sigla", "Conselho")
st.set_page_config(page_title=f"Análise {sigla_conselho}", layout="wide", initial_sidebar_state="collapsed")

# --- CSS AVANÇADO (Mantido) ---
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-baseweb="input"] { background-color: #e1effe !important; border: 1px solid #b3d7ff !important; border-radius: 8px !important; }
    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }
    .stTabs [data-baseweb="tab-list"] { position: sticky !important; top: 45px !important; z-index: 999 !important; background-color: white !important; padding-top: 15px; border-bottom: 2px solid #f0f2f6; }
    .stTabs button[role="tab"] p { font-size: 20px !important; font-weight: 700 !important; }
    .cabecalho-container { display: flex; align-items: center; gap: 40px; margin-bottom: 20px; padding: 10px; }
    .cabecalho-logos { background-color: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 20px; }
    .logo-pref { height: 120px; width: auto; }
    .logo-cmtt { height: 80px; width: auto; }
    .cabecalho-textos { text-align: left; border-left: 2px solid #ddd; padding-left: 30px; }
    .cabecalho-titulo { margin: 0; color: #2C3E50; font-size: 32px; font-weight: 800; }
    .cabecalho-sub { margin: 0; color: #7f8c8d; font-size: 18px; }
    .cabecalho-desc { margin: 10px 0 0 0; color: #34495e; font-size: 14px; line-height: 1.2; }
    @media (max-width: 800px) { .cabecalho-container { flex-direction: column; text-align: center; } .cabecalho-textos { border-left: none; border-top: 2px solid #ddd; padding-top: 15px; } }
    </style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)


# --- Funções de Apoio (Mantidas) ---
def criar_padrao_flexivel(termo_busca):
    palavras = termo_busca.strip().split()
    if not palavras: return None
    padrao = r".*?".join([re.escape(p) for p in palavras])
    return re.compile(padrao, re.IGNORECASE)


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria(carimbo_cache):
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return [doc for lista_docs in dados.values() for doc in lista_docs] if isinstance(dados, dict) else dados
    return []


# --- Cabeçalho (Mantido) ---
try:
    with open(config_ambiente.CAMINHO_LOGO1, "rb") as img1, open(config_ambiente.CAMINHO_LOGO2, "rb") as img2:
        b64_logo1, b64_logo2 = base64.b64encode(img1.read()).decode(), base64.b64encode(img2.read()).decode()
        st.markdown(f"""
        <div class="cabecalho-container">
            <div class="cabecalho-logos"><img class="logo-pref" src="data:image/png;base64,{b64_logo1}"><img class="logo-cmtt" src="data:image/jpeg;base64,{b64_logo2}"></div>
            <div class="cabecalho-textos"><h1 class="cabecalho-titulo">ANÁLISE CMTT</h1><p class="cabecalho-sub">Protótipo elaborado em código aberto</p>
            <p class="cabecalho-desc"><strong>Núcleo de Participação em Mobilidade Urbana</strong><br>SMT - Secretaria Municipal de Mobilidade e Trânsito</p></div>
        </div>""", unsafe_allow_html=True)
except:
    st.warning("⚠️ Erro nos logos.")

# --- Navegação Principal (Abas "Catálogo" Removida) ---
tab_busca, tab_temas, tab_frequencia = st.tabs(["🔍 Buscador", "📊 Temas", "👥 Frequência"])

# ==============================================================================
# ABA 1: BUSCADOR (Lógica Original Preservada)
# ==============================================================================
with tab_busca:
    termo = st.text_input("O que você procura nas Atas e Planilhas?",
                          placeholder="Ex: Tarifa Zero, Nome de Conselheiro...")
    if termo:
        corpus = carregar_corpus_memoria(os.path.getmtime(CAMINHO_CACHE) if os.path.exists(CAMINHO_CACHE) else 0)
        regex = criar_padrao_flexivel(termo)
        res = [{"Fonte": d["Fonte"], "Data": d.get("Data", ""), "Contexto": l.strip()} for d in corpus for l in
               d.get("Lines", []) if regex.search(l)]
        if res:
            st.success(f"Encontrados {len(res)} resultados.")
            st.table(pd.DataFrame(res))
        else:
            st.info("Nenhum resultado encontrado.")

# ==============================================================================
# ABA 2: PAINEL TEMÁTICO (Alterações Solicitadas)
# ==============================================================================
with tab_temas:
    try:
        df_evo = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_evolucao_anual.csv"), sep=';',
                             encoding='utf-8-sig')
        st.subheader("📈 Evolução da Relevância Média Anual (%)")  # Alteração de Título

        fig_evo = px.line(df_evo, x='Ano', y='Relevancia_Media_Anual', color='Tema_Classificado', markers=True,
                          template="plotly_white")
        fig_evo.update_layout(
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                font=dict(size=14)  # Aumento da letra da legenda
            ),
            xaxis=dict(type='category')
        )
        st.plotly_chart(fig_evo, use_container_width=True)
    except:
        st.error("Erro ao carregar dados temáticos.")

# ==============================================================================
# ABA 3: FREQUÊNCIA (Nova Lógica Detalhada)
# ==============================================================================
with tab_frequencia:
    st.markdown("## 👥 Frequência e Engajamento Histórico")

    # 1. Balanço dos Dados (Métricas Solicitadas)
    m1, m2, m3, m4 = st.columns(4)
    # Valores automáticos (Serão calculados do Relatorio_Cadeiras_Absenteismo.xlsx)
    m1.metric("Segmento mais frequente (%)", "Poder Público (92%)")
    m2.metric("Segmento menos frequente (%)", "Operadores (68%)")
    m3.metric("Cadeira mais presente (%)", "SMT (98%)")
    m4.metric("Cadeira menos presente (%)", "Sindicato X (45%)")

    st.write("---")

    # 2. Gráfico de Assiduidade (Eixo X com todos os anos)
    st.subheader("📈 Evolução da Assiduidade nas Reuniões Plenárias")
    anos_completo = [str(a) for a in range(2014, 2026)]
    valores_mock = [65, 68, 72, 80, 78, 75, 82, 85, 88, 84, 82, 80]  # Substituir por lógica de média anual

    fig_assid = go.Figure(go.Scatter(x=anos_completo, y=valores_mock, fill='tozeroy', line_color='#005088'))
    fig_assid.update_layout(xaxis=dict(type='category', title="Ano"), yaxis_title="Presença %", height=350)
    st.plotly_chart(fig_assid, use_container_width=True)

    st.write("---")

    # 3. Detalhamento por Segmento (Sub-abas)
    st.subheader("🏛️ Assiduidade Detalhada por Cadeira")
    sub_pub, sub_soc, sub_ope, sub_conv = st.tabs(["Poder Público", "Sociedade Civil", "Operadores", "Convidados"])

    with sub_pub:
        st.markdown("### Ranking: Poder Público")
        # Aqui entra o px.bar filtrado pela coluna 'Segmento' == 'Poder Público' da sua Matriz_Snapshot_IA
        st.info("Gráfico automático das secretarias aparecerá aqui.")

    with sub_soc:
        st.markdown("### Ranking: Sociedade Civil")
        # Filtro: 'Segmento' == 'Sociedade Civil'
        st.info("Gráfico automático das entidades civis aparecerá aqui.")

    with sub_ope:
        st.markdown("### Ranking: Operadores")
        # Filtro: 'Segmento' == 'Operadores'
        st.info("Gráfico automático dos sindicatos/empresas aparecerá aqui.")

    with sub_conv:
        st.markdown("### Ranking: Convidados e Visitantes")
        # Busca no arquivo 'visitantes_geral.csv'
        st.info("Ranking dos 15 visitantes mais frequentes aparecerá aqui.")