import sys
import os
import re
import json
import shutil
import base64
import pandas as pd
import streamlit as st
import plotly.express as px  # 🆕 NOVA BIBLIOTECA PARA OS GRÁFICOS DO BI
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# O Streamlit às vezes perde a raiz do projeto, então garantimos que ele ache a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas

# A ÚNICA MUDANÇA: Importamos o construtor centralizado de cache!
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

    /* CSS para deixar a barra de busca azul clara */
    div[data-baseweb="input"] {
        background-color: #e1effe !important;
        border: 1px solid #b3d7ff !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] > div {
        background-color: transparent !important;
    }
    input[type="text"] {
        background-color: transparent !important;
    }

    /* CSS para a tabela de resultados corporativa */
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


# --- NOVIDADE: O Olho de Hórus do Arquivo (Carimbos de Tempo) ---
def get_carimbo_tempo(caminho):
    """Lê a dados/hora exata da última modificação do arquivo no sistema."""
    return os.path.getmtime(caminho) if os.path.exists(caminho) else 0


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria(carimbo_cache):
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            # Se for o cache particionado (dicionário), achata para o buscador varrer tudo
            if isinstance(dados, dict):
                return [doc for lista_docs in dados.values() for doc in lista_docs]
            return dados
    return []


@st.cache_data(show_spinner=False)
def carregar_fontes_extras(carimbo_mandatos, carimbo_index):
    extras = []
    fontes = {
        "base_mandatosCMTT.xlsx": CAMINHO_BASE_MANDATOS,
        "index_atasCMTT.xlsx": CAMINHO_INDEX_EXCEL
    }

    for nome_arquivo, caminho in fontes.items():
        if os.path.exists(caminho):
            try:
                caminho_temp = caminho + ".tmp"
                shutil.copy2(caminho, caminho_temp)
                dict_abas = pd.read_excel(caminho_temp, sheet_name=None)

                for nome_aba, df_aba in dict_abas.items():
                    if not df_aba.empty:
                        linhas_df = df_aba.astype(str).agg(' | '.join, axis=1).tolist()
                        extras.append({
                            "Fonte": f"{nome_arquivo} (Aba: {nome_aba})",
                            "Data": "Tabela Oficial",
                            "Reunião": "Dados Estruturados",
                            "Linhas": linhas_df
                        })
                os.remove(caminho_temp)
            except Exception as e:
                print(f"⚠️ Erro ao ler {nome_arquivo}: {e}")
        else:
            print(f"⚠️ Ficheiro não encontrado: {nome_arquivo}")

    return extras


# --- Barra Lateral ---
st.sidebar.header("⚙️ Configurações")
senha_admin = st.sidebar.text_input("Senha de Admin para Manutenção:", type="password")

if senha_admin == config_ambiente.SENHA_ADMIN:
    st.sidebar.warning("Modo Administrador Ativo")
    if st.sidebar.button("🔄 Reconstruir Cache (Geral)"):
        st.cache_data.clear()

        # Ajuste leve: como removemos a função interna, usamos o spinner nativo do Streamlit
        with st.spinner("Lendo PDFs e reconstruindo cérebro de buscas... Isso pode demorar alguns minutos."):
            if construir_cache_novo():
                st.sidebar.success("Cache atualizado!")
                st.rerun()
else:
    if os.path.exists(CAMINHO_CACHE):
        st.sidebar.success("✅ Sistema Pronto")
    else:
        st.sidebar.error("⚠️ Cache não encontrado. Contate o administrador.")
st.sidebar.markdown("---")

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
except Exception as e:
    st.warning("⚠️ Não foi possível carregar os logos no cabeçalho. Verifique os caminhos e arquivos.")

st.write("---")

# ==============================================================================
# 🆕 ESTRUTURA DE ABAS (SUPER APP)
# ==============================================================================
tab_busca, tab_temas, tab_frequencia, tab_catalogo = st.tabs([
    "🔍 Buscador de Atas",
    "📊 Painel Temático",
    "👥 Frequência e Interesse",
    "📚 Catálogo Histórico"
])

# ==============================================================================
# ABA 1: O BUSCADOR DE TEXTO
# ==============================================================================
with tab_busca:
    _, col_miolo, _ = st.columns([1, 6, 1])

    with col_miolo:
        st.markdown(
            f"<h3 style='text-align: center; color: #2C3E50; margin-bottom: 25px;'>🔍 Digite para buscar nas bases do {sigla_conselho}</h3>",
            unsafe_allow_html=True)

        # --- A MÁGICA DOS CARIMBOS DE TEMPO AQUI ---
        carimbo_cache = get_carimbo_tempo(CAMINHO_CACHE)
        carimbo_mandatos = get_carimbo_tempo(CAMINHO_BASE_MANDATOS)
        carimbo_index = get_carimbo_tempo(CAMINHO_INDEX_EXCEL)

        corpus_completo = carregar_corpus_memoria(carimbo_cache) + carregar_fontes_extras(carimbo_mandatos,
                                                                                          carimbo_index)

        if corpus_completo:
            termo = st.text_input("Busca Oculta", label_visibility="collapsed", placeholder="O que você procura?")

            # --- Filtro de Ano ---
            anos_unicos = sorted(list(set(str(doc.get("Data", "N/A")) for doc in corpus_completo)), reverse=True)
            anos_selecionados = st.multiselect(
                "📅 Filtrar por Ano (Opcional):",
                options=anos_unicos,
                default=[],
                placeholder="Selecione um ou mais anos (deixe vazio para buscar em todo o acervo)"
            )

            st.markdown(
                "<p style='text-align: center; color: #6c757d; font-size: 16px; margin-top: 12px;'>💡 Dica: Use termos entre aspas para buscas mais específicas ou apenas palavras-chave para busca flexível.</p>",
                unsafe_allow_html=True)

            _, col_btn, _ = st.columns([2, 1, 2])
            with col_btn:
                st.button("PESQUISAR", use_container_width=True)
        else:
            termo = ""
            st.warning("⚠️ Base de dados vazia. Reconstrua o cache na barra lateral.")

    # --- Área de Resultados ---
    if termo and corpus_completo:
        st.write("---")
        st.markdown(
            f"<p style='text-align: center;'><em>Pesquisando em <strong>{len(corpus_completo)}</strong> documentos e bases...</em></p>",
            unsafe_allow_html=True)

        regex = criar_padrao_flexivel(termo)
        resultados = []

        for doc in corpus_completo:
            data_doc = str(doc.get("Data", "N/A"))

            # Aplica o filtro de ano (pula o arquivo inteiro se o ano não estiver selecionado)
            if anos_selecionados and data_doc not in anos_selecionados:
                continue

            for linha in doc["Linhas"]:
                if regex.search(linha):
                    resultados.append({
                        "Fonte": doc.get("Fonte", "N/A"),
                        "Data": data_doc,
                        "Reunião/Origem": doc.get("Reunião", "N/A"),
                        "Contexto": linha.strip()
                    })

        if resultados:
            df_res = pd.DataFrame(resultados)
            st.success(f"Encontradas {len(df_res)} ocorrências!")


            # Função para gerar a URL bruta para o GitHub
            def gerar_url(fonte_str):
                nome_arquivo = fonte_str.split(" (Aba:")[0].strip()
                usuario = config_ambiente.GITHUB_USER
                repo = config_ambiente.GITHUB_REPO
                branch = config_ambiente.GITHUB_BRANCH

                if nome_arquivo.endswith('.pdf'):
                    return f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/pdf_atas_pleno/{nome_arquivo}"
                elif nome_arquivo.endswith('.xlsx'):
                    return f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/{nome_arquivo}"
                return ""


            # --- A) PREPARANDO A TABELA PARA O CSV ---
            df_csv = df_res.copy()
            df_csv['Link Original'] = df_csv['Fonte'].apply(gerar_url)

            # --- B) PREPARANDO A TABELA PARA A TELA (HTML Embutido) ---
            df_tela = df_res.copy()


            def aplicar_html(fonte_str):
                url = gerar_url(fonte_str)
                is_pdf = fonte_str.endswith('.pdf')
                icone = "📕" if is_pdf else "📗"

                if url:
                    return f'<a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none; font-weight: bold;">{icone} {fonte_str}</a>'
                return fonte_str


            df_tela['Fonte'] = df_tela['Fonte'].apply(aplicar_html)

            # Exibe a tabela na tela renderizando o HTML
            tabela_html = df_tela.to_html(escape=False, index=False, classes="tabela-resultados")
            st.write(tabela_html, unsafe_allow_html=True)

            st.write("---")

            csv_bytes = df_csv.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            data_hoje = pd.Timestamp.now().strftime("%Y-%m-%d")
            nome_arquivo_csv = f"busca_{sigla_conselho}_{termo.replace(' ', '_')}_{data_hoje}.csv"

            st.download_button(
                label="📊 Baixar Tabela de Resultados (CSV)",
                data=csv_bytes,
                file_name=nome_arquivo_csv,
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning(f"∅ Nada encontrado para o termo '{termo}'.")

# ==============================================================================
# ABA 2: PAINEL TEMÁTICO (O Novo BI)
# ==============================================================================
with tab_temas:
    st.markdown("## 📊 Análise Temática e Histórica das Pautas")
    st.write("Acompanhe a evolução dos temas debatidos no conselho.")

    # 1. Carregando os Dados
    try:
        caminho_evolucao = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_evolucao_anual.csv")
        caminho_debatidos = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv")
        caminho_palavras = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_nuvem_palavras.csv")

        df_evolucao = pd.read_csv(caminho_evolucao, sep=';', encoding='utf-8-sig')
        df_debatidos = pd.read_csv(caminho_debatidos, sep=';', encoding='utf-8-sig')
        df_palavras = pd.read_csv(caminho_palavras, sep=';', encoding='utf-8-sig')

        dados_carregados = True
    except Exception as e:
        st.warning(
            "⚠️ Os dados do Painel Temático ainda não foram gerados. Certifique-se de ter rodado o `relatorio_tematico.py` primeiro.")
        dados_carregados = False

    if dados_carregados:
        # --- APLICAÇÃO DA NOTA METODOLÓGICA (As Réguas de Corte) ---
        def classificar_relevancia(val):
            if val >= 25.0:
                return '1: Pauta Dominante (> 25%)'
            elif val >= 12.0:
                return '2: Debate Consolidado (12% a 25%)'
            else:
                return '3: Informes e Menções (5% a 11.9%)'


        df_debatidos['Categoria_Metodologica'] = df_debatidos['Relevancia_(%)'].apply(classificar_relevancia)

        # --- FILTROS DO DASHBOARD ---
        temas_unicos = sorted(df_evolucao['Tema_Classificado'].unique())

        col_filtro1, col_filtro2 = st.columns([2, 1])
        with col_filtro1:
            temas_selecionados = st.multiselect(
                "🎯 Selecione os Temas para comparar:",
                options=temas_unicos,
                default=temas_unicos[:3]  # Mostra os 3 primeiros por padrão para não poluir
            )

        if temas_selecionados:
            st.write("---")

            # --- GRÁFICO 1: EVOLUÇÃO HISTÓRICA (Linhas) ---
            st.subheader("📈 Evolução da Relevância Média Anual")
            df_evo_filtrado = df_evolucao[df_evolucao['Tema_Classificado'].isin(temas_selecionados)]

            fig_evo = px.line(
                df_evo_filtrado,
                x='Ano',
                y='Relevancia_Media_Anual',
                color='Tema_Classificado',
                markers=True,
                labels={'Relevancia_Media_Anual': 'Relevância Média (%)', 'Tema_Classificado': 'Tema'},
                template="plotly_white"
            )
            fig_evo.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_evo, use_container_width=True)

            st.write("---")
            col_graf2, col_graf3 = st.columns(2)

            # --- GRÁFICO 2: INTENSIDADE DO DEBATE (Barras) ---
            with col_graf2:
                st.subheader("🔥 Profundidade da Pauta nas Atas")
                st.caption("Baseado na classificação percentual das pautas.")

                df_deb_filtrado = df_debatidos[df_debatidos['Tema_Classificado'].isin(temas_selecionados)]

                contagem_categorias = df_deb_filtrado.groupby(
                    ['Tema_Classificado', 'Categoria_Metodologica']).size().reset_index(name='Qtd_Reunioes')

                fig_cat = px.bar(
                    contagem_categorias,
                    x='Tema_Classificado',
                    y='Qtd_Reunioes',
                    color='Categoria_Metodologica',
                    labels={'Qtd_Reunioes': 'Nº de Reuniões', 'Tema_Classificado': 'Tema'},
                    color_discrete_map={
                        '1: Pauta Dominante (> 25%)': '#d62728',  # Vermelho
                        '2: Debate Consolidado (12% a 25%)': '#ff7f0e',  # Laranja
                        '3: Informes e Menções (5% a 11.9%)': '#1f77b4'  # Azul
                    },
                    template="plotly_white"
                )
                fig_cat.update_layout(legend_title_text='Nível de Profundidade')
                st.plotly_chart(fig_cat, use_container_width=True)

                # --- GRÁFICO 3: NUVEM DE PALAVRAS (Gatilhos) ---
                with col_graf3:
                    st.subheader("☁️ Nuvem de Palavras (Gatilhos)")
                    st.caption("Termos que puxaram a classificação destes temas.")

                    df_pal_filtrado = df_palavras[df_palavras['Tema'].isin(temas_selecionados)]
                    top_palavras = df_pal_filtrado.groupby('Palavra')['Vezes_Ativada'].sum().reset_index()

                    if not top_palavras.empty:
                        # Converte o dataframe para um dicionário {Palavra: Frequência}
                        freq_dict = dict(zip(top_palavras['Palavra'], top_palavras['Vezes_Ativada']))

                        # Desenha a Nuvem de Palavras
                        wordcloud = WordCloud(
                            width=800,
                            height=550,
                            background_color='white',
                            colormap='Greens',  # Mantém a identidade visual verde
                            max_words=100,
                            contour_width=0
                        ).generate_from_frequencies(freq_dict)

                        # Renderiza a imagem gerada dentro do Streamlit
                        fig, ax = plt.subplots(figsize=(8, 5.5))
                        ax.imshow(wordcloud, interpolation='bilinear')
                        ax.axis('off')  # Esconde as bordas do gráfico
                        st.pyplot(fig, clear_figure=True)
                    else:
                        st.info("Nenhuma palavra encontrada para o filtro atual.")

# ==============================================================================
# ABA 3: FREQUÊNCIA E INTERESSE
# ==============================================================================
with tab_frequencia:
    st.info("🚧 Em construção: Aqui entrarão os dados de Absenteísmo e Interesse por Segmento.")

# ==============================================================================
# ABA 4: CATÁLOGO HISTÓRICO
# ==============================================================================
with tab_catalogo:
    st.info("🚧 Em construção: Aqui entrarão as tabelas de Evolução de Secretarias e Histórico de Conselheiros.")