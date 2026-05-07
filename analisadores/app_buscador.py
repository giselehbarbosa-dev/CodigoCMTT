import sys
import os
import re
import json
import shutil
import base64
import pandas as pd
import streamlit as st
import plotly.express as px
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

# --- CSS AVANÇADO: Cabeçalho, Abas Gigantes e Fixas ---
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Inputs e Busca */
    div[data-baseweb="input"] { background-color: #e1effe !important; border: 1px solid #b3d7ff !important; border-radius: 8px !important; }

    /* Tabela de Resultados */
    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }

    /* TRUQUE: Ocultar o "Select All" em inglês */
    div[data-testid="stMultiSelect"] ul[role="listbox"] li#bui11 { display: none !important; }
    div[data-baseweb="select"] ul li:first-child { display: none !important; }

    /* FIXAR ABAS NO TOPO (Sticky) */
    .stTabs [data-baseweb="tab-list"] {
        position: fixed;
        top: 0;
        z-index: 1001;
        width: 100%;
        background-color: rgba(255, 255, 255, 0.0) !important; /* Fundo transparente */
        padding-top: 10px;
        padding-bottom: 10px;
    }

    /* Aumentar fonte das abas */
    .stTabs button[role="tab"] p {
        font-size: 22px !important;
        font-weight: 700 !important;
    }

    /* Ajuste para o conteúdo não ficar por baixo das abas fixas */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px;
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


# --- Cabeçalho Lateralizado (Logo + Texto) ---
caminho_logo1 = config_ambiente.CAMINHO_LOGO1
caminho_logo2 = config_ambiente.CAMINHO_LOGO2

try:
    with open(caminho_logo1, "rb") as img1, open(caminho_logo2, "rb") as img2:
        b64_logo1 = base64.b64encode(img1.read()).decode()
        b64_logo2 = base64.b64encode(img2.read()).decode()

        html_header = f"""
        <div style="display: flex; align-items: center; gap: 40px; margin-bottom: 30px; padding: 10px;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <img src="data:image/png;base64,{b64_logo1}" style="height: 120px; width: auto;">
                <img src="data:image/jpeg;base64,{b64_logo2}" style="height: 80px; width: auto;">
            </div>
            <div style="text-align: left; border-left: 2px solid #ddd; padding-left: 30px;">
                <h1 style="margin: 0; color: #2C3E50; font-size: 32px; font-weight: 800;">ANÁLISE CMTT</h1>
                <p style="margin: 0; color: #7f8c8d; font-size: 18px;">Protótipo elaborado em código aberto</p>
                <p style="margin: 10px 0 0 0; color: #34495e; font-size: 14px; line-height: 1.2;">
                    <strong>Núcleo de Participação em Mobilidade Urbana - Assessoria Técnica</strong><br>
                    Secretaria Municipal de Mobilidade Urbana e Transporte
                </p>
            </div>
        </div>
        """
        st.markdown(html_header, unsafe_allow_html=True)
except Exception:
    st.warning("⚠️ Erro ao carregar cabeçalho.")

st.write("---")

# --- Abas ---
tab_busca, tab_temas, tab_frequencia, tab_catalogo = st.tabs([
    "🔍 Buscador", "📊 Temas", "👥 Frequência", "📚 Catálogo"
])

# ==============================================================================
# ABA 1: BUSCADOR
# ==============================================================================
with tab_busca:
    st.markdown("### 🔍 Pesquisa de Atas e Documentos")
    carimbo_cache = get_carimbo_tempo(CAMINHO_CACHE)
    corpus = carregar_corpus_memoria(carimbo_cache)

    if corpus:
        termo = st.text_input("O que você procura?", placeholder="Digite palavras-chave...")
        if termo:
            st.info(f"Resultados para: {termo}")
            # Lógica de busca aqui...
    else:
        st.warning("Base de dados não carregada.")

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
            temas_sel = st.multiselect("🎯 Temas:", options=temas_todos, default=temas_todos)
        with col_f2:
            anos_disp = sorted(df_evolucao['Ano'].astype(str).unique(), reverse=True)
            anos_sel = st.multiselect("📅 Anos:", options=anos_disp, default=anos_disp)

        if temas_sel and anos_sel:
            # Gráfico de Evolução
            df_evo = df_evolucao[df_evolucao['Tema'].isin(temas_sel)].sort_values('Ano')
            fig_evo = px.line(df_evo, x='Ano', y='Relevancia_Media_Anual', color='Tema', markers=True,
                              color_discrete_map=mapa_cores, template="plotly_white")
            fig_evo.update_xaxes(type='category')
            fig_evo.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                  height=400)
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
                    mask = ((x - 225) ** 2 / (200 ** 2) + (y - 400) ** 2 / (380 ** 2) > 1).astype(int) * 255

                    wc = WordCloud(width=800, height=450, background_color=None, mode="RGBA", mask=mask, margin=10,
                                   prefer_horizontal=0.85, color_func=cor_func).generate_from_frequencies(freq_dict)
                    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='none')
                    ax.imshow(wc, interpolation='bilinear');
                    ax.axis('off')
                    st.pyplot(fig, clear_figure=True, transparent=True)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

with tab_frequencia: st.info("🚧 Aba de Frequência em construção.")
with tab_catalogo: st.info("🚧 Aba de Catálogo em construção.")