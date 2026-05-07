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
from wordcloud import WordCloud

# Configura o Plotly para Português (Brasil)
pio.templates.default = "plotly_white"

# O Streamlit às vezes perde a raiz do projeto, então garantimos que ele ache a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas
from construtores.construtor_cache import construir_cache_novo

CAMINHO_CACHE = config_ambiente.CAMINHO_CACHE_BUSCADOR
CAMINHO_BASE_MANDATOS = config_ambiente.CAMINHO_EXCEL_MANDATOS
CAMINHO_INDEX_EXCEL = config_ambiente.CAMINHO_EXCEL_INDEX
DIR_BASE = config_ambiente.BASE_DIR

# --- Configuração da Página ---
sigla_conselho = config_ambiente.REGRAS_CONSELHO.get("sigla", "Conselho")
st.set_page_config(page_title=f"Busca{sigla_conselho}", layout="wide", initial_sidebar_state="collapsed")

# --- Identidade Visual e Limpeza de UI ---
esconder_estilo = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    div[data-baseweb="input"] { background-color: #e1effe !important; border: 1px solid #b3d7ff !important; border-radius: 8px !important; }
    div[data-baseweb="input"] > div { background-color: transparent !important; }
    input[type="text"] { background-color: transparent !important; }

    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; color: #31333F; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; color: #31333F; }
    .tabela-resultados tr:hover { background-color: #f8f9fa; }
    </style>
"""
st.markdown(esconder_estilo, unsafe_allow_html=True)


# --- Funções de Apoio ---
def criar_padrao_flexivel(termo_busca):
    palavras = termo_busca.strip().split()
    if not palavras: return None
    padrao = r".*?".join([re.escape(p) for p in palavras])
    return re.compile(padrao, re.IGNORECASE)


def ordenacao_natural(texto):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(texto))]


def get_carimbo_tempo(caminho):
    return os.path.getmtime(caminho) if os.path.exists(caminho) else 0


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria(carimbo_cache):
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            if isinstance(dados, dict):
                return [doc for lista_docs in dados.values() for doc in lista_docs]
            return dados
    return []


@st.cache_data(show_spinner=False)
def carregar_fontes_extras(carimbo_mandatos, carimbo_index):
    extras = []
    fontes = {"base_mandatosCMTT.xlsx": CAMINHO_BASE_MANDATOS, "index_atasCMTT.xlsx": CAMINHO_INDEX_EXCEL}
    for nome_arquivo, caminho in fontes.items():
        if os.path.exists(caminho):
            try:
                caminho_temp = caminho + ".tmp"
                shutil.copy2(caminho, caminho_temp)
                dict_abas = pd.read_excel(caminho_temp, sheet_name=None)
                for nome_aba, df_aba in dict_abas.items():
                    if not df_aba.empty:
                        linhas_df = df_aba.astype(str).agg(' | '.join, axis=1).tolist()
                        extras.append({"Fonte": f"{nome_arquivo} (Aba: {nome_aba})", "Data": "Tabela Oficial",
                                       "Reunião": "Dados Estruturados", "Linhas": linhas_df})
                os.remove(caminho_temp)
            except Exception:
                pass
    return extras


def encurtar_nomes_temas(tema):
    if not isinstance(tema, str): return tema
    tema = tema.replace("Mobilidade Ativa: ", "")
    tema = tema.replace("Mobilidade Urbana: ", "")
    tema = tema.replace("Transporte Individual: ", "")
    tema = tema.replace("Transporte Público Coletivo", "Transporte Coletivo")
    return tema


# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações")
senha_admin = st.sidebar.text_input("Senha de Admin para Manutenção:", type="password")
if senha_admin == config_ambiente.SENHA_ADMIN:
    st.sidebar.warning("Modo Administrador Ativo")
    if st.sidebar.button("🔄 Reconstruir Cache (Geral)"):
        st.cache_data.clear()
        with st.spinner("Lendo PDFs e reconstruindo cérebro de buscas..."):
            if construir_cache_novo():
                st.sidebar.success("Cache atualizado!")
                st.rerun()

# --- Cabeçalho e Logos ---
caminho_logo1 = config_ambiente.CAMINHO_LOGO1
caminho_logo2 = config_ambiente.CAMINHO_LOGO2
try:
    with open(caminho_logo1, "rb") as img1, open(caminho_logo2, "rb") as img2:
        b64_logo1 = base64.b64encode(img1.read()).decode()
        b64_logo2 = base64.b64encode(img2.read()).decode()
        html_cabecalho = f"""
        <div style="display: flex; justify-content: center; margin-bottom: 2rem; margin-top: 1rem;">
            <div style="background-color: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 30px; max-width: 95%;">
                <img src="data:image/png;base64,{b64_logo1}" style="height: 100px; width: auto; max-width: 100%; object-fit: contain;">
                <img src="data:image/jpeg;base64,{b64_logo2}" style="height: 70px; width: auto; max-width: 100%; object-fit: contain;">
            </div>
        </div>
        """
        st.markdown(html_cabecalho, unsafe_allow_html=True)
except Exception:
    st.warning("⚠️ Logos não carregados.")
st.write("---")

# --- Área Principal ---
tab_busca, tab_temas, tab_frequencia, tab_catalogo = st.tabs([
    "🔍 Buscador de Atas", "📊 Painel Temático", "👥 Frequência e Interesse", "📚 Catálogo Histórico"
])

# ABA 1: BUSCADOR
with tab_busca:
    _, col_miolo, _ = st.columns([1, 6, 1])
    with col_miolo:
        st.markdown(
            f"<h3 style='text-align: center; color: #2C3E50; margin-bottom: 25px;'>🔍 Pesquise nas bases do {sigla_conselho}</h3>",
            unsafe_allow_html=True)
        carimbo_cache, carimbo_mandatos, carimbo_index = get_carimbo_tempo(CAMINHO_CACHE), get_carimbo_tempo(
            CAMINHO_BASE_MANDATOS), get_carimbo_tempo(CAMINHO_INDEX_EXCEL)
        corpus_completo = carregar_corpus_memoria(carimbo_cache) + carregar_fontes_extras(carimbo_mandatos,
                                                                                          carimbo_index)

        if corpus_completo:
            termo = st.text_input("Digite sua busca", label_visibility="collapsed", placeholder="O que você procura?")
            col_f_ano, col_f_ata = st.columns(2)
            with col_f_ano:
                anos_unicos = sorted(list(set(str(doc.get("Data", "N/A")) for doc in corpus_completo)), reverse=True)
                anos_selecionados = st.multiselect("📅 Filtrar por Ano:", options=anos_unicos, default=[],
                                                   placeholder="Todos os anos")
            with col_f_ata:
                lista_atas_bruta = list(set(str(doc.get("Reunião", "N/A")) for doc in corpus_completo if
                                            doc.get("Reunião") != "Dados Estruturados"))
                atas_unicas = sorted(lista_atas_bruta, key=ordenacao_natural)
                atas_selecionadas = st.multiselect("📌 Filtrar por Ata:", options=atas_unicas, default=[],
                                                   placeholder="Todas as atas")

            st.markdown(
                "<p style='text-align: center; color: #6c757d; font-size: 16px; margin-top: 12px;'>💡 Dica: Use termos entre aspas para buscas exatas.</p>",
                unsafe_allow_html=True)
            _, col_btn, _ = st.columns([2, 1, 2])
            with col_btn:
                st.button("PESQUISAR", use_container_width=True)
        else:
            st.warning("⚠️ Base de dados vazia.")

    if termo and corpus_completo:
        st.write("---")
        regex = criar_padrao_flexivel(termo)
        resultados = []
        for doc in corpus_completo:
            data_doc, nome_ata = str(doc.get("Data", "N/A")), str(doc.get("Reunião", "N/A"))
            if anos_selecionados and data_doc not in anos_selecionados: continue
            if atas_selecionadas and nome_ata not in atas_selecionadas: continue
            for linha in doc["Lines" if "Lines" in doc else "Linhas"]:
                if regex.search(linha):
                    resultados.append({"Fonte": doc.get("Fonte", "N/A"), "Data": data_doc, "Reunião/Origem": nome_ata,
                                       "Contexto": linha.strip()})

        if resultados:
            df_res = pd.DataFrame(resultados)
            st.success(f"Encontradas {len(df_res)} ocorrências!")


            def gerar_url(fonte_str):
                nome_arq = fonte_str.split(" (Aba:")[0].strip()
                usr, repo, br = config_ambiente.GITHUB_USER, config_ambiente.GITHUB_REPO, config_ambiente.GITHUB_BRANCH
                if nome_arq.endswith('.pdf'):
                    return f"https://raw.githubusercontent.com/{usr}/{repo}/{br}/dados/base_dados/pdf_atas_pleno/{nome_arq}"
                elif nome_arq.endswith('.xlsx'):
                    return f"https://raw.githubusercontent.com/{usr}/{repo}/{br}/dados/base_dados/{nome_arq}"
                return ""


            df_csv = df_res.copy()
            df_csv['Link Original'] = df_csv['Fonte'].apply(gerar_url)
            df_tela = df_res.copy()


            def aplicar_html(fonte_str):
                url, is_pdf = gerar_url(fonte_str), fonte_str.endswith('.pdf')
                if url: return f'<a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none;">{"📕" if is_pdf else "📗"} {fonte_str}</a>'
                return fonte_str


            df_tela['Fonte'] = df_tela['Fonte'].apply(aplicar_html)
            st.write(df_tela.to_html(escape=False, index=False, classes="tabela-resultados"), unsafe_allow_html=True)
            st.write("---")
            csv_bytes = df_csv.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📊 Baixar Tabela (CSV)", data=csv_bytes,
                               file_name=f"busca_CMTT_{termo.replace(' ', '_')}.csv", mime="text/csv",
                               use_container_width=True)

# ABA 2: PAINEL TEMÁTICO
with tab_temas:
    st.markdown("## 📊 Análise Temática e Histórica")
    try:
        df_evolucao = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_evolucao_anual.csv"),
                                  sep=';', encoding='utf-8-sig')
        df_debatidos = pd.read_csv(os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv"), sep=';',
                                   encoding='utf-8-sig')
        df_palavras = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_nuvem_palavras.csv"),
                                  sep=';', encoding='utf-8-sig')
        dados_carregados = True
    except Exception:
        st.warning("⚠️ Dados não encontrados. Rode os motores de análise primeiro.")
        dados_carregados = False

    if dados_carregados:
        df_evolucao['Tema'] = df_evolucao['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Tema'] = df_debatidos['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Ano'] = df_debatidos['Data (AAAA/MM)'].astype(str).str[:4]
        df_palavras['Tema'] = df_palavras['Tema'].apply(encurtar_nomes_temas)

        # Paleta de Cores Estática
        temas_todos = sorted(df_evolucao['Tema'].unique())
        paleta = px.colors.qualitative.Alphabet + px.colors.qualitative.Vivid
        mapa_cores = {t: paleta[i % len(paleta)] for i, t in enumerate(temas_todos)}

        # CORREÇÃO: Segurança Viária agora é Amarelo Escuro/Ouro para não sumir no cinza
        if "Segurança Viária" in mapa_cores:
            mapa_cores["Segurança Viária"] = "#D4AF37"

        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            temas_selecionados = st.multiselect("🎯 Temas para Destacar:", options=temas_todos, default=temas_todos,
                                                placeholder="Selecione os temas...")
        with col_t2:
            anos_disp = sorted(df_evolucao['Ano'].astype(str).unique(), reverse=True)
            anos_selecionados = st.multiselect("📅 Anos de Análise:", options=anos_disp, default=anos_disp,
                                               placeholder="Selecione os anos...")

        if temas_selecionados and anos_selecionados:
            st.write("---")
            # Gráfico de linhas ignora o filtro de ano para mostrar o contexto completo
            df_evo_completo = df_evolucao[df_evolucao['Tema'].isin(temas_selecionados)].sort_values('Ano')

            df_deb_filtrado = df_debatidos[df_debatidos['Ano'].astype(str).isin(anos_selecionados)]

            # --- GRÁFICO 1: EVOLUÇÃO ---
            st.subheader("📈 Evolução da Relevância Média Anual (Série Completa)")
            fig_evo = px.line(
                df_evo_completo, x='Ano', y='Relevancia_Media_Anual', color='Tema',
                markers=True, color_discrete_map=mapa_cores,
                labels={'Relevancia_Media_Anual': 'Relevância (%)', 'Ano': 'Ano', 'Tema': 'Assunto'},
                template="plotly_white"
            )
            # CORREÇÃO: Força todos os anos no eixo X
            fig_evo.update_xaxes(type='category', tickmode='linear')
            fig_evo.update_layout(
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=-0.15),
                legend_title_text="", margin=dict(l=200)
            )
            st.plotly_chart(fig_evo, use_container_width=True, config={'locale': 'pt-BR'})

            st.write("---")
            col_g2, col_g3 = st.columns(2)

            # --- GRÁFICO 2: BARRAS ---
            with col_g2:
                st.subheader("📋 Contagem de Reuniões por Tema")
                contagem = df_deb_filtrado.groupby('Tema')['Arquivo'].nunique().reset_index(name='Qtd').sort_values(
                    'Qtd')
                contagem['Cor'] = contagem['Tema'].apply(
                    lambda t: mapa_cores.get(t) if t in temas_selecionados else '#EAEAEA')
                fig_bar = px.bar(
                    contagem, x='Qtd', y='Tema', orientation='h', text='Qtd',
                    labels={'Qtd': 'Reuniões', 'Tema': ''}, template="plotly_white"
                )
                fig_bar.update_traces(marker_color=contagem['Cor'])
                # CORREÇÃO: Alinhamento de altura com a Nuvem
                fig_bar.update_layout(showlegend=False, height=550)
                st.plotly_chart(fig_bar, use_container_width=True, config={'locale': 'pt-BR'})

            # --- GRÁFICO 3: NUVEM ---
            with col_g3:
                st.subheader("☁️ Nuvem de Palavras (Gatilhos)")
                stopwords_bi = ['conselheiro', 'conselheiros', 'conselho', 'conselhos', 'representante',
                                'representantes']
                df_pal_limpo = df_palavras[~df_palavras['Palavra'].str.lower().isin(stopwords_bi)]
                top_p = df_pal_limpo.groupby('Palavra')['Vezes_Ativada'].sum().reset_index()

                if not top_p.empty:
                    freq_dict = dict(zip(top_p['Palavra'], top_p['Vezes_Ativada']))
                    idx_max = df_pal_limpo.groupby('Palavra')['Vezes_Ativada'].idxmax()
                    tema_pal = df_pal_limpo.loc[idx_max, ['Palavra', 'Tema']].set_index('Palavra')['Tema'].to_dict()


                    def cor_func(word, **kwargs):
                        t = tema_pal.get(word)
                        return mapa_cores.get(t, "#333333") if t in temas_selecionados else "#EAEAEA"


                    # CORREÇÃO: Alinhamento de altura com o Gráfico de Barras
                    wordcloud = WordCloud(
                        width=800, height=550, background_color='white', max_words=150,
                        relative_scaling=0.3, max_font_size=70, color_func=cor_func
                    ).generate_from_frequencies(freq_dict)

                    fig, ax = plt.subplots(figsize=(8, 5.5))
                    ax.imshow(wordcloud, interpolation='bilinear');
                    ax.axis('off')
                    st.pyplot(fig, clear_figure=True)
        else:
            st.info("👆 Selecione os filtros acima.")

with tab_frequencia: st.info("🚧 Em construção.")
with tab_catalogo: st.info("🚧 Em construção.")