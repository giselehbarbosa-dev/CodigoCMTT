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

# --- CSS AVANÇADO REVISADO (Foco em Mobile e Texto) ---
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Layout Geral */
    .main .block-container { padding-top: 2rem; }

    /* Cabeçalho Compacto e Responsivo */
    .cabecalho-container { display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px; flex-wrap: nowrap; }
    .cabecalho-logos { background-color: white; padding: 10px 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 15px; flex-shrink: 0; }
    .logo-pref { height: 70px; width: auto; }
    .logo-cmtt { height: 50px; width: auto; }
    .cabecalho-textos { text-align: left; border-left: 2px solid #ddd; padding-left: 20px; flex-grow: 1; min-width: 0; }
    .cabecalho-titulo { margin: 0; color: #2C3E50; font-size: 24px; font-weight: 800; line-height: 1.1; }
    .cabecalho-sub { margin: 2px 0; color: #7f8c8d; font-size: 14px; font-weight: 600; }
    .cabecalho-desc { margin: 5px 0 0 0; color: #34495e; font-size: 11px; line-height: 1.2; }

    /* Tabela de Resultados */
    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }

    /* Estilo das Abas */
    .stTabs [data-baseweb="tab-list"] { position: sticky; top: 0; z-index: 999; background-color: white; border-bottom: 2px solid #f0f2f6; }
    .stTabs button[role="tab"] p { font-size: 18px !important; font-weight: 700 !important; }

    /* Inputs e Busca */
    div[data-baseweb="input"] { background-color: #f8fbff !important; border-radius: 8px !important; }

    /* TRUQUE: Ocultar o "Select All" em inglês */
    div[data-testid="stMultiSelect"] ul[role="listbox"] li#bui11 { display: none !important; }
    div[data-baseweb="select"] ul li:first-child { display: none !important; }

    /* Responsividade Celular */
    @media (max-width: 800px) {
        .cabecalho-container { flex-direction: column; gap: 10px; align-items: center; text-align: center; }
        .cabecalho-logos { padding: 8px 12px; }
        .logo-pref { height: 55px; }
        .logo-cmtt { height: 35px; }
        .cabecalho-textos { border-left: none; border-top: 1px solid #ddd; padding-left: 0; padding-top: 10px; width: 100%; }
        .cabecalho-titulo { font-size: 20px; }
        .cabecalho-sub { font-size: 13px; }
        .cabecalho-desc { font-size: 10px; }
        .stTabs button[role="tab"] p { font-size: 16px !important; }
    }
    </style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)


# --- Funções de Apoio ---
def criar_padrao_flexivel(termo_busca):
    palavras = termo_busca.strip().split()
    if not palavras: return None
    padrao = r".*?".join([re.escape(p) for p in palavras])
    return re.compile(padrao, re.IGNORECASE)


def ordenacao_natural(texto):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(texto))]


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


# --- Cabeçalho Limpo ---
caminho_logo1 = config_ambiente.CAMINHO_LOGO1
caminho_logo2 = config_ambiente.CAMINHO_LOGO2

try:
    with open(caminho_logo1, "rb") as img1, open(caminho_logo2, "rb") as img2:
        b64_logo1 = base64.b64encode(img1.read()).decode()
        b64_logo2 = base64.b64encode(img2.read()).decode()

        html_header = f"""
        <div class="cabecalho-container">
            <div class="cabecalho-logos">
                <img class="logo-pref" src="data:image/png;base64,{b64_logo1}">
                <img class="logo-cmtt" src="data:image/jpeg;base64,{b64_logo2}">
            </div>
            <div class="cabecalho-textos">
                <h1 class="cabecalho-titulo">ANÁLISE CMTT</h1>
                <p class="cabecalho-sub">Conselho Municipal de Trânsito e Transporte</p>
                <p class="cabecalho-desc">
                    Assessoria Técnica / Núcleo de Participação em Mobilidade Urbana<br>
                    Secretaria Municipal de Mobilidade e Trânsito - SMT
                </p>
            </div>
        </div>
        """
        st.markdown(html_header, unsafe_allow_html=True)
except Exception:
    st.warning("⚠️ Erro ao carregar cabeçalho.")

# --- Abas ---
tab_busca, tab_temas, tab_frequencia = st.tabs([
    "🔍 Buscador", "📊 Temas", "👥 Frequência"
])

# ==============================================================================
# ABA 1: BUSCADOR
# ==============================================================================
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

# ==============================================================================
# ABA 2: PAINEL TEMÁTICO
# ==============================================================================
with tab_temas:
    dados_carregados = False
    try:
        df_evolucao = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_evolucao_anual.csv"),
                                  sep=';', encoding='utf-8-sig')
        df_debatidos = pd.read_csv(os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv"), sep=';',
                                   encoding='utf-8-sig')
        df_palavras = pd.read_csv(os.path.join(config_ambiente.CAMINHO_RELATORIOS, "bi_temas_nuvem_palavras.csv"),
                                  sep=';', encoding='utf-8-sig')
        dados_carregados = True
    except Exception as e:
        st.warning(f"⚠️ Dados não encontrados. Rode os motores de análise primeiro. Detalhe: {e}")

    if dados_carregados:
        df_evolucao['Tema'] = df_evolucao['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Tema'] = df_debatidos['Tema_Classificado'].apply(encurtar_nomes_temas)
        df_debatidos['Ano'] = df_debatidos['Data (AAAA/MM)'].astype(str).str[:4]
        df_palavras['Tema'] = df_palavras['Tema'].apply(encurtar_nomes_temas)

        temas_todos = sorted(df_evolucao['Tema'].unique())
        paleta = px.colors.qualitative.Alphabet + px.colors.qualitative.Vivid
        mapa_cores = {t: paleta[i % len(paleta)] for i, t in enumerate(temas_todos)}
        if "Segurança Viária" in mapa_cores:
            mapa_cores["Segurança Viária"] = "#D4AF37"

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            temas_sel = st.multiselect("🎯 Temas:", options=temas_todos, default=temas_todos)
        with col_f2:
            anos_disp = sorted(df_evolucao['Ano'].astype(str).unique(), reverse=True)
            anos_sel = st.multiselect("📅 Anos:", options=anos_disp, default=anos_disp)

        if temas_sel and anos_sel:
            st.write("---")
            df_evo_completo = df_evolucao[df_evolucao['Tema'].isin(temas_sel)].sort_values('Ano')
            df_deb_filtrado = df_debatidos[df_debatidos['Ano'].astype(str).isin(anos_sel)]

            st.subheader("📈 Evolução da Relevância Média Anual (%)")
            fig_evo = px.line(
                df_evo_completo, x='Ano', y='Relevancia_Media_Anual', color='Tema',
                markers=True, color_discrete_map=mapa_cores,
                labels={'Relevancia_Media_Anual': 'Relevância (%)', 'Ano': 'Ano', 'Tema': ''}, template="plotly_white"
            )
            fig_evo.update_xaxes(type='category', tickmode='linear', tickangle=-45)
            fig_evo.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.3,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14)
                ),
                margin=dict(l=20, r=20, t=30, b=100)
            )
            st.plotly_chart(fig_evo, use_container_width=True, config={'locale': 'pt-BR'})

            st.write("---")
            col_g2, col_g3 = st.columns(2)

            with col_g2:
                st.subheader("📋 Contagem de Reuniões por Tema")
                contagem = df_deb_filtrado.groupby('Tema')['Arquivo'].nunique().reset_index(name='Qtd').sort_values(
                    'Qtd')
                contagem['Cor'] = contagem['Tema'].apply(lambda t: mapa_cores.get(t) if t in temas_sel else '#EAEAEA')
                fig_bar = px.bar(
                    contagem, x='Qtd', y='Tema', orientation='h', text='Qtd',
                    labels={'Qtd': 'Reuniões', 'Tema': ''}, template="plotly_white"
                )
                fig_bar.update_traces(marker_color=contagem['Cor'])
                fig_bar.update_layout(
                    showlegend=False,
                    height=450,
                    margin=dict(l=0, r=10, t=20, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_bar, use_container_width=True, config={'locale': 'pt-BR'})

            with col_g3:
                st.subheader("☁️ Nuvem de Palavras")
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
                        return mapa_cores.get(t, "#333333") if t in temas_sel else "#EAEAEA"


                    x, y = np.ogrid[:450, :800]
                    mask = ((x - 225) ** 2 / (210 ** 2) + (y - 400) ** 2 / (380 ** 2) > 1).astype(int) * 255

                    wc = WordCloud(
                        width=800, height=450,
                        background_color=None, mode="RGBA",
                        mask=mask,
                        margin=10,
                        prefer_horizontal=0.85,
                        max_words=120,
                        min_font_size=12,
                        max_font_size=80,
                        color_func=cor_func
                    ).generate_from_frequencies(freq_dict)

                    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='none')
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig, clear_figure=True, transparent=True)
                else:
                    st.info("Nenhuma palavra encontrada.")
        else:
            st.info("👆 Selecione os filtros acima.")

# ==============================================================================
# ABA 3: FREQUÊNCIA E ENGAJAMENTO HISTÓRICO
# ==============================================================================
with tab_frequencia:
    st.markdown("## 👥 Frequência e Engajamento Histórico")

    caminho_relatorio = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "Relatorio_Cadeiras_Absenteismo.xlsx")
    caminho_catalogo = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "Catálogo_de_Metadados_CMTT.xlsx")

    try:
        # --- 1. Carregamento e Pré-Processamento ---
        df_cadeiras = pd.read_excel(caminho_relatorio)

        # Filtro de Governança: Excluir Secretaria Executiva dos cálculos estatísticos
        df_cadeiras = df_cadeiras[df_cadeiras['Segmento'] != 'SECRETARIA EXECUTIVA']

        # Calcula a % de Presença dinamicamente
        df_cadeiras['Presenca_Perc'] = (df_cadeiras['Pres'] / df_cadeiras['Total'] * 100).round(1).fillna(0)

        COL_CADEIRA = 'Cadeira'
        COL_SEGMENTO = 'Segmento'
        COL_PRESENCA = 'Presenca_Perc'

        # --- 2. O CATÁLOGO NO TOPO (Para Contexto) ---
        with st.expander("📚 CONTEXTO: Catálogo de Nomenclaturas e Mandatos", expanded=True):
            st.markdown(
                "Utilize a tabela abaixo para entender como as cadeiras mudaram de nome ao longo dos anos. A busca nos gráficos utiliza o nome **Padronizado**.")
            try:
                df_catalogo = pd.read_excel(caminho_catalogo, sheet_name=None)
                aba_alvo = 'Evolução_das_Secretarias' if 'Evolução_das_Secretarias' in df_catalogo else \
                list(df_catalogo.keys())[0]
                df_cat_full = df_catalogo[aba_alvo]

                # Remove a secretaria executiva do catálogo exibido também
                df_cat_full = df_cat_full[df_cat_full['Segmento'] != 'SECRETARIA EXECUTIVA']

                # Exibe a tabela adaptável para celular (sem cortes)
                st.dataframe(df_cat_full, use_container_width=True, hide_index=True)

                # Criação do dicionário para as Tooltips
                dict_historico = {}
                for _, row in df_cat_full.iterrows():
                    cadeira_padrao = str(row.get('Cadeira Padronizada', ''))
                    if not cadeira_padrao or cadeira_padrao == 'nan': continue

                    linha_tempo = []
                    ultimo_nome = ""
                    for col in df_cat_full.columns[2:]:
                        valor = str(row[col]).strip()
                        if valor not in ['-', 'nan', 'NaN', 'None', '']:
                            if valor != ultimo_nome:
                                ano_ref = str(col).split('_')[0][:4]
                                linha_tempo.append(f"<b>{ano_ref}:</b> {valor}")
                                ultimo_nome = valor

                    dict_historico[cadeira_padrao] = "<br>".join(
                        linha_tempo) if linha_tempo else "Sem mudanças registradas."
            except Exception as e_cat:
                dict_historico = {}
                st.info("Catálogo indisponível no momento.")

        st.write("---")

        # --- 3. Balanço dos Dados (Métricas Reais) ---
        seg_media = df_cadeiras.groupby(COL_SEGMENTO)[COL_PRESENCA].mean()

        cad_maior_idx = df_cadeiras[COL_PRESENCA].idxmax()
        cad_menor_idx = df_cadeiras[COL_PRESENCA].idxmin()

        # Encurtar o nome da cadeira caso seja muito longo para a caixa da métrica
        nome_cad_maior = str(df_cadeiras.loc[cad_maior_idx, COL_CADEIRA])
        nome_cad_menor = str(df_cadeiras.loc[cad_menor_idx, COL_CADEIRA])
        if len(nome_cad_maior) > 18: nome_cad_maior = nome_cad_maior[:18] + "..."
        if len(nome_cad_menor) > 18: nome_cad_menor = nome_cad_menor[:18] + "..."

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Segmento Mais Ativo", f"{seg_media.idxmax()}", f"{seg_media.max():.1f}%")
        m2.metric("Menor Frequência", f"{seg_media.idxmin()}", f"{seg_media.min():.1f}%")
        m3.metric("Cadeira Top Presença", f"{nome_cad_maior}", f"{df_cadeiras.loc[cad_maior_idx, COL_PRESENCA]:.1f}%")
        m4.metric("Cadeira Mais Ausente", f"{nome_cad_menor}", f"{df_cadeiras.loc[cad_menor_idx, COL_PRESENCA]:.1f}%")

        # --- 4. Evolução Temporal ---
        st.subheader("📈 Assiduidade nas Reuniões Plenárias")
        anos_f = [str(a) for a in range(2014, 2026)]
        pres_f = [68, 72, 80, 78, 75, 82, 85, 88, 84, 82, 80, 81]  # Exemplo temporário para a série temporal
        fig_at = go.Figure(go.Scatter(x=anos_f, y=pres_f, fill='tozeroy', line_color='#005088'))
        fig_at.update_layout(xaxis=dict(type='category', title="Ano"), yaxis=dict(range=[0, 100]), height=300,
                             margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_at, use_container_width=True)

        # --- 5. Detalhamento por Segmento (Sub-abas) ---
        st.subheader("🏛️ Participação por Cadeira")
        t_pub, t_soc, t_op, t_conv = st.tabs(["Poder Público", "Sociedade Civil", "Operadores", "Convidados"])


        def plot_bar(df, segmento, cor):
            dff = df[df[COL_SEGMENTO].str.contains(segmento, case=False, na=False)].copy()
            dff = dff.sort_values(COL_PRESENCA, ascending=True)

            if dff.empty:
                st.info("Não há dados.")
                return

            # Adiciona o histórico
            dff['Historico_Tooltip'] = dff[COL_CADEIRA].map(dict_historico).fillna("Informação histórica não mapeada.")

            fig = px.bar(
                dff,
                x=COL_PRESENCA,
                y=COL_CADEIRA,
                orientation='h',
                text=COL_PRESENCA,
                custom_data=['Historico_Tooltip']
            )

            hovertemplate_personalizado = (
                "<b>%{y}</b><br>"
                "Assiduidade: %{x}%<br><br>"
                "<b>Histórico de Nomenclaturas:</b><br>"
                "%{customdata[0]}<extra></extra>"
            )

            fig.update_traces(
                marker_color=cor,
                texttemplate='%{text}%',
                textposition='outside',
                hovertemplate=hovertemplate_personalizado
            )

            fig.update_layout(
                xaxis=dict(range=[0, max(100, dff[COL_PRESENCA].max() + 15)], title="Presença (%)"),
                yaxis_title="",
                height=max(300, len(dff) * 45),
                margin=dict(l=0, r=20, t=10, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)


        with t_pub:
            plot_bar(df_cadeiras, 'ÓRGÃOS MUNICIPAIS', '#2E4D68')
        with t_soc:
            plot_bar(df_cadeiras, 'SOCIEDADE CIVIL', '#11caa0')
        with t_op:
            plot_bar(df_cadeiras, 'OPERADORES', '#D4AF37')
        with t_conv:
            plot_bar(df_cadeiras, 'CONVIDADOS', '#888888')

    except Exception as e:
        st.error(f"Erro ao processar frequência: {e}")