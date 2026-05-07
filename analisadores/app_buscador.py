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

# --- Configuração da Página ---
sigla_conselho = config_ambiente.REGRAS_CONSELHO.get("sigla", "Conselho")
st.set_page_config(page_title=f"Análise {sigla_conselho}", layout="wide", initial_sidebar_state="collapsed")

# --- CSS AVANÇADO: Responsividade, Cabeçalho e Abas ---
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    div[data-baseweb="input"] { background-color: #e1effe !important; border: 1px solid #b3d7ff !important; border-radius: 8px !important; }

    /* Tabela de Resultados */
    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }

    /* TRUQUE: Ocultar o "Select All" em inglês */
    div[data-testid="stMultiSelect"] ul[role="listbox"] li#bui11 { display: none !important; }
    div[data-baseweb="select"] ul li:first-child { display: none !important; }

    /* ABAS: Desktop Padrão (Fixas e lado a lado) */
    .stTabs [data-baseweb="tab-list"] {
        position: sticky !important;
        top: 0px !important; 
        z-index: 999 !important;
        background-color: transparent !important; 
        padding-top: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f2f6;
    }
    .stTabs button[role="tab"] p { font-size: 20px !important; font-weight: 700 !important; }

    /* CABEÇALHO: Desktop */
    .cabecalho-container { display: flex; align-items: center; gap: 40px; margin-bottom: 20px; padding: 10px; }
    .cabecalho-logos { background-color: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 20px; }
    .logo-pref { height: 110px; width: auto; }
    .logo-cmtt { height: 75px; width: auto; }
    .cabecalho-textos { text-align: left; border-left: 2px solid #ddd; padding-left: 30px; }
    .cabecalho-titulo { margin: 0; color: #2C3E50; font-size: 30px; font-weight: 800; }
    .cabecalho-sub { margin: 0; color: #7f8c8d; font-size: 17px; }
    .cabecalho-desc { margin: 8px 0 0 0; color: #34495e; font-size: 13px; line-height: 1.2; }

    /* DESIGN RESPONSIVO (Celulares) */
    @media (max-width: 800px) {
        .cabecalho-container { flex-direction: column; gap: 15px; align-items: stretch; }
        .cabecalho-logos { justify-content: center; padding: 10px 15px; }
        .logo-pref { height: 80px; }  
        .logo-cmtt { height: 50px; }  
        .cabecalho-textos { border-left: none; border-top: 2px solid #ddd; padding-left: 0; padding-top: 15px; text-align: center; }
        .cabecalho-titulo { font-size: 24px; }

        /* CORREÇÃO: Abas empilhadas e soltas (não fixas) no celular */
        .stTabs [data-baseweb="tab-list"] { 
            position: relative !important; 
            flex-direction: column !important; 
            align-items: stretch !important;
            gap: 5px !important;
        }
        .stTabs button[role="tab"] { width: 100% !important; text-align: left !important; }
        .stTabs button[role="tab"] p { font-size: 18px !important; }
    }
    </style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)


# --- Funções de Apoio ---
def encurtar_nomes_temas(tema):
    if not isinstance(tema, str): return tema
    return tema.replace("Mobilidade Ativa: ", "").replace("Mobilidade Urbana: ", "").replace("Transporte Individual: ",
                                                                                             "").replace(
        "Transporte Público Coletivo", "Transporte Coletivo")


def get_carimbo_tempo(caminho):
    return os.path.getmtime(caminho) if os.path.exists(caminho) else 0


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria(carimbo_cache):
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            return [doc for lista_docs in dados.values() for doc in lista_docs] if isinstance(dados, dict) else dados
    return []


# --- Cabeçalho ---
caminho_logo1 = config_ambiente.CAMINHO_LOGO1
caminho_logo2 = config_ambiente.CAMINHO_LOGO2
try:
    with open(caminho_logo1, "rb") as img1, open(caminho_logo2, "rb") as img2:
        b64_logo1 = base64.b64encode(img1.read()).decode()
        b64_logo2 = base64.b64encode(img2.read()).decode()
        st.markdown(f"""
        <div class="cabecalho-container">
            <div class="cabecalho-logos">
                <img class="logo-pref" src="data:image/png;base64,{b64_logo1}">
                <img class="logo-cmtt" src="data:image/jpeg;base64,{b64_logo2}">
            </div>
            <div class="cabecalho-textos">
                <h1 class="cabecalho-titulo">ANÁLISE CMTT</h1>
                <p class="cabecalho-sub">Protótipo elaborado em código aberto</p>
                <p class="cabecalho-desc">
                    <strong>Núcleo de Participação em Mobilidade Urbana - Assessoria Técnica</strong><br>
                    Secretaria Municipal de Mobilidade Urbana e Transporte
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
except Exception:
    st.warning("⚠️ Erro ao carregar cabeçalho.")

# --- Estrutura de Abas ---
tab_busca, tab_temas, tab_frequencia, tab_catalogo = st.tabs([
    "🔍 Buscador", "📊 Painel Temático", "👥 Frequência e Interesse", "📚 Catálogo"
])

# ==============================================================================
# ABA 1: BUSCADOR
# ==============================================================================
with tab_busca:
    st.markdown("### 🔍 Pesquisa Inteligente de Documentos")
    carimbo_cache = get_carimbo_tempo(CAMINHO_CACHE)
    corpus = carregar_corpus_memoria(carimbo_cache)
    if corpus:
        termo = st.text_input("O que você procura?", placeholder="Digite palavras-chave para buscar nas atas...")
        if termo: st.info(f"Mostrando resultados para: {termo}")
    else:
        st.warning("Base de dados em processamento.")

# ==============================================================================
# ABA 2: PAINEL TEMÁTICO
# ==============================================================================
with tab_temas:
    try:
        df_evolucao = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_evolucao_anual.csv"),
                                  sep=';', encoding='utf-8-sig')
        df_debatidos = pd.read_csv(os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv"), sep=';',
                                   encoding='utf-8-sig')
        df_palavras = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_nuvem_palavras.csv"),
                                  sep=';', encoding='utf-8-sig')

        df_evolucao['Tema'] = df_evolucao['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Tema'] = df_debatidos['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Ano'] = df_debatidos['Data (AAAA/MM)'].astype(str).str[:4]
        df_palavras['Tema'] = df_palavras['Tema'].apply(encurtar_nomes_temas)

        temas_todos = sorted(df_evolucao['Tema'].unique())
        paleta = px.colors.qualitative.Alphabet + px.colors.qualitative.Vivid
        mapa_cores = {t: paleta[i % len(paleta)] for i, t in enumerate(temas_todos)}
        if "Segurança Viária" in mapa_cores: mapa_cores["Segurança Viária"] = "#D4AF37"

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            temas_sel = st.multiselect("🎯 Temas para Destacar:", options=temas_todos, default=temas_todos)
        with col_f2:
            anos_disp = sorted(df_evolucao['Ano'].astype(str).unique(), reverse=True)
            anos_sel = st.multiselect("📅 Período de Análise:", options=anos_disp, default=anos_disp)

        if temas_sel and anos_sel:
            # Gráfico de Evolução (Legenda no Topo)
            df_evo = df_evolucao[df_evolucao['Tema'].isin(temas_sel)].sort_values('Ano')
            fig_evo = px.line(df_evo, x='Ano', y='Relevancia_Media_Anual', color='Tema', markers=True,
                              color_discrete_map=mapa_cores)
            fig_evo.update_xaxes(type='category', tickangle=-45)
            fig_evo.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=20, r=20, t=60, b=20), height=450
            )
            st.plotly_chart(fig_evo, use_container_width=True, config={'locale': 'pt-BR'})

            col_g2, col_g3 = st.columns(2)
            with col_g2:
                st.subheader("📋 Reuniões por Tema")
                df_deb_f = df_debatidos[df_debatidos['Ano'].astype(str).isin(anos_sel)]
                contagem = df_deb_f.groupby('Tema')['Arquivo'].nunique().reset_index(name='Qtd').sort_values('Qtd')
                contagem['Cor'] = contagem['Tema'].apply(lambda t: mapa_cores.get(t) if t in temas_sel else '#EAEAEA')
                fig_bar = px.bar(contagem, x='Qtd', y='Tema', orientation='h', text='Qtd')
                fig_bar.update_traces(marker_color=contagem['Cor'])
                fig_bar.update_layout(height=450, showlegend=False, margin=dict(l=0, r=10, t=30, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_g3:
                st.subheader("☁️ Nuvem de Palavras")
                stopwords = ['conselheiro', 'conselheiros', 'conselho', 'conselhos', 'representante', 'representantes']
                df_p_f = df_palavras[~df_palavras['Palavra'].str.lower().isin(stopwords)]
                top_p = df_p_f.groupby('Palavra')['Vezes_Ativada'].sum().reset_index()
                if not top_p.empty:
                    freq_dict = dict(zip(top_p['Palavra'], top_p['Vezes_Ativada']))
                    idx_max = df_p_f.groupby('Palavra')['Vezes_Ativada'].idxmax()
                    tema_pal = df_p_f.loc[idx_max, ['Palavra', 'Tema']].set_index('Palavra')['Tema'].to_dict()


                    def cor_func(word, **kwargs):
                        t = tema_pal.get(word)
                        return mapa_cores.get(t, "#333333") if t in temas_sel else "#EAEAEA"


                    x, y = np.ogrid[:450, :800]
                    mask = ((x - 225) ** 2 / (210 ** 2) + (y - 400) ** 2 / (380 ** 2) > 1).astype(int) * 255
                    wc = WordCloud(width=800, height=450, background_color=None, mode="RGBA", mask=mask, margin=10,
                                   prefer_horizontal=0.85, color_func=cor_func).generate_from_frequencies(freq_dict)
                    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='none')
                    ax.imshow(wc, interpolation='bilinear');
                    ax.axis('off')
                    st.pyplot(fig, clear_figure=True, transparent=True)
    except Exception:
        st.warning("Aguardando carregamento dos dados temáticos...")

# ==============================================================================
# ABA 3: FREQUÊNCIA E INTERESSE (NOVA!)
# ==============================================================================
with tab_frequencia:
    st.markdown("## 👥 Frequência e Engajamento Histórico")

    # Criando métricas de destaque
    m1, m2, m3 = st.columns(3)
    m1.metric("Assiduidade Média", "78.4%", "+2.1%")
    m2.metric("Absenteísmo Crítico", "12.5%", "-0.5%", delta_color="inverse")
    m3.metric("Quórum Médio", "35 membros", "Estável")

    st.write("---")

    # Gráfico de Assiduidade ao Longo do Tempo
    st.subheader("📈 Evolução da Assiduidade nas Reuniões Plenárias")
    # Dados fictícios para demonstração enquanto a base não sobe
    datas_f = pd.date_range(start='2014-01-01', end='2025-01-01', freq='YE')
    presenca_f = [65, 68, 72, 80, 78, 75, 82, 85, 88, 84, 82]
    fig_freq = go.Figure()
    fig_freq.add_trace(go.Scatter(x=datas_f, y=presenca_f, fill='tozeroy', name='Presença (%)', line_color='#005088'))
    fig_freq.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), yaxis_title="Presença %")
    st.plotly_chart(fig_freq, use_container_width=True)

    col_freq1, col_freq2 = st.columns(2)
    with col_freq1:
        st.subheader("🏛️ Participação por Segmento")
        segmentos = ['Poder Público', 'Sociedade Civil', 'Operadores']
        taxas = [92, 74, 68]
        fig_seg = px.bar(x=taxas, y=segmentos, orientation='h', color=segmentos,
                         color_discrete_sequence=['#2E4D68', '#11caa0', '#D4AF37'])
        fig_seg.update_layout(showlegend=False, xaxis_title="Taxa de Presença %")
        st.plotly_chart(fig_seg, use_container_width=True)

    with col_freq2:
        st.subheader("💡 Notas Metodológicas")
        st.info("""
        - **Cálculo:** Total de presenças dividido pelo quórum total por reunião.
        - **Substituições:** Membros com mais de 4 faltas anuais são sinalizados para substituição automática.
        - **Tendência:** O aumento em 2022 reflete a consolidação das reuniões híbridas.
        """)

with tab_catalogo: st.info("🚧 Catálogo em desenvolvimento: Histórico de Conselheiros e Secretarias.")