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

# --- CSS RESPONSIVO REFINADO ---
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Layout Geral */
    .main .block-container { padding-top: 1.5rem; }

    /* Cabeçalho Profissional e Responsivo */
    .cabecalho-container { display: flex; align-items: center; gap: 25px; margin-bottom: 25px; padding: 15px; flex-wrap: nowrap; overflow: hidden; }
    .cabecalho-logos { background-color: white; padding: 12px; border-radius: 12px; display: flex; align-items: center; gap: 15px; flex-shrink: 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }

    .logo-pref { height: 90px; width: auto; }
    .logo-cmtt { height: 70px; width: auto; }

    .cabecalho-textos { text-align: left; border-left: 2px solid #ddd; padding-left: 25px; flex-grow: 1; min-width: 0; }
    .cabecalho-titulo { margin: 0; color: #2C3E50; font-size: 1.6rem; font-weight: 800; line-height: 1.1; }
    .cabecalho-sub { margin: 4px 0; color: #d32f2f; font-size: 0.95rem; font-weight: 700; text-transform: uppercase; }
    .cabecalho-desc { margin: 6px 0 0 0; color: #34495e; font-size: 0.85rem; line-height: 1.4; }

    /* Tabela de Resultados */
    .tabela-resultados { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
    .tabela-resultados th { background-color: #f0f2f6; padding: 12px; text-align: left; border-bottom: 2px solid #ccc; }
    .tabela-resultados td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }

    /* Estilo das Abas */
    .stTabs [data-baseweb="tab-list"] { position: sticky; top: 0; z-index: 999; background-color: white; border-bottom: 2px solid #f0f2f6; }
    .stTabs button[role="tab"] p { font-size: 1.1rem !important; font-weight: 700 !important; }

    /* Inputs e Busca */
    div[data-baseweb="input"] { background-color: #f8fbff !important; border-radius: 8px !important; border: 1px solid #b3d7ff !important; }

    @media (max-width: 800px) {
        .cabecalho-container { flex-direction: column; align-items: center; text-align: center; gap: 15px; }
        .cabecalho-textos { border-left: none; border-top: 2px solid #ddd; padding-left: 0; padding-top: 15px; width: 100%; }
        .cabecalho-titulo { font-size: 1.3rem; }
        .logo-pref { height: 65px; }
        .logo-cmtt { height: 50px; }
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


# --- Cabeçalho Oficial ---
try:
    with open(config_ambiente.CAMINHO_LOGO1, "rb") as img1, open(config_ambiente.CAMINHO_LOGO2, "rb") as img2:
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
                <p class="cabecalho-sub">⚠️ Protótipo em Código Aberto - Fase de Testes</p>
                <p class="cabecalho-desc">
                    Núcleo de Participação em Mobilidade Urbana da Assessoria Técnica<br>
                    Secretaria Municipal de Mobilidade Urbana e Transporte de São Paulo (SMT/SP)<br>
                    <strong>Sistema Beta:</strong> Verifique os dados antes de utilizá-los oficialmente.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
except Exception:
    st.title(f"Análise {sigla_conselho}")

# --- Navegação ---
tab_busca, tab_temas, tab_frequencia = st.tabs(["🔍 Buscador", "📊 Temas", "👥 Frequência"])

# ==============================================================================
# ABA 1: BUSCADOR
# ==============================================================================
with tab_busca:
    _, col_miolo, _ = st.columns([1, 6, 1])
    with col_miolo:
        st.markdown(
            f"<h3 style='text-align: center; color: #2C3E50; margin-bottom: 25px;'>🔍 Pesquise nas bases do {sigla_conselho}</h3>",
            unsafe_allow_html=True)
        corpus_completo = carregar_corpus_memoria(get_carimbo_tempo(CAMINHO_CACHE)) + carregar_fontes_extras(
            get_carimbo_tempo(CAMINHO_BASE_MANDATOS), get_carimbo_tempo(CAMINHO_INDEX_EXCEL))

        if corpus_completo:
            # 1. Abre o formulário
            with st.form(key="form_busca"):
                termo = st.text_input("Digite sua busca", label_visibility="collapsed",
                                      placeholder="O que você deseja buscar?")

                col_f_ano, col_f_ata = st.columns(2)
                with col_f_ano:
                    anos_unicos = sorted(list(set(str(doc.get("Data", "N/A")) for doc in corpus_completo)),
                                         reverse=True)
                    anos_selecionados = st.multiselect("📅 Filtrar por Ano:", options=anos_unicos, default=[],
                                                       placeholder="Todos os anos")
                with col_f_ata:
                    lista_atas_bruta = list(set(str(doc.get("Reunião", "N/A")) for doc in corpus_completo if
                                                doc.get("Reunião") != "Dados Estruturados"))
                    atas_unicas = sorted(lista_atas_bruta, key=ordenacao_natural)
                    atas_selecionadas = st.multiselect("📌 Filtrar por Ata:", options=atas_unicas, default=[],
                                                       placeholder="Todas as atas")

                st.markdown(
                    "<p style='text-align: center; color: #6c757d; font-size: 14px; margin-top: 12px;'>💡 Dica: Use termos entre aspas para buscas exatas.</p>",
                    unsafe_allow_html=True)

                _, col_btn, _ = st.columns([2, 1, 2])
                with col_btn:
                    # 2. O botão agora fica salvo em uma variável
                    clicou_pesquisar = st.form_submit_button("PESQUISAR", use_container_width=True)

            # 3. A SUA LÓGICA ORIGINAL COMEÇA AQUI! (Apenas troque a linha do 'if st.button...' por esta:)
            if clicou_pesquisar and termo:
                st.write("---")
                regex = criar_padrao_flexivel(termo)
                resultados = []
                for doc in corpus_completo:
                    if anos_selecionados and str(doc.get("Data", "N/A")) not in anos_selecionados: continue
                    if atas_selecionadas and str(doc.get("Reunião", "N/A")) not in atas_selecionadas: continue
                    for linha in doc.get("Lines", doc.get("Linhas", [])):
                        if regex.search(linha):
                            resultados.append({"Fonte": doc.get("Fonte", "N/A"), "Data": doc.get("Data", "N/A"),
                                               "Reunião/Origem": doc.get("Reunião", "N/A"), "Contexto": linha.strip()})

                if resultados:
                    df_res = pd.DataFrame(resultados)
                    st.success(f"Encontradas {len(df_res)} ocorrências!")


                    def aplicar_html(fonte_str):
                        usr, repo, br = config_ambiente.GITHUB_USER, config_ambiente.GITHUB_REPO, config_ambiente.GITHUB_BRANCH
                        nome_arq = fonte_str.split(" (Aba:")[0].strip()
                        url = f"https://raw.githubusercontent.com/{usr}/{repo}/{br}/dados/base_dados/{'pdf_atas_pleno/' if nome_arq.endswith('.pdf') else ''}{nome_arq}"
                        return f'<a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none;">{"📕" if nome_arq.endswith(".pdf") else "📗"} {fonte_str}</a>'


                    df_tela = df_res.copy()
                    df_tela['Fonte'] = df_tela['Fonte'].apply(aplicar_html)
                    st.write(df_tela.to_html(escape=False, index=False, classes="tabela-resultados"),
                             unsafe_allow_html=True)
                    csv_bytes = df_res.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button("📊 Baixar Tabela (CSV)", data=csv_bytes,
                                       file_name=f"busca_CMTT_{termo.replace(' ', '_')}.csv", mime="text/csv",
                                       use_container_width=True)
                else:
                    st.info("Nenhum resultado encontrado.")

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

        for df in [df_evolucao, df_debatidos, df_palavras]:
            if 'Tema_Classificado' in df.columns:
                df['Tema'] = df['Tema_Classificado'].apply(encurtar_nomes_temas)
            elif 'Tema' in df.columns:
                df['Tema'] = df['Tema'].apply(encurtar_nomes_temas)

        df_debatidos['Ano'] = df_debatidos['Data (AAAA/MM)'].astype(str).str[:4]
        temas_todos = sorted(df_evolucao['Tema'].unique())
        paleta = px.colors.qualitative.Alphabet + px.colors.qualitative.Vivid
        mapa_cores = {t: paleta[i % len(paleta)] for i, t in enumerate(temas_todos)}
        if "Segurança Viária" in mapa_cores: mapa_cores["Segurança Viária"] = "#D4AF37"

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            temas_sel = st.multiselect("🎯 Temas:", options=temas_todos, default=temas_todos)
        with col_f2:
            anos_sel = st.multiselect("📅 Anos:", options=sorted(df_evolucao['Ano'].astype(str).unique(), reverse=True),
                                      default=sorted(df_evolucao['Ano'].astype(str).unique()))

        if temas_sel and anos_sel:
            st.write("---")
            st.subheader("📈 Evolução da Relevância Média Anual (%)")
            fig_evo = px.line(df_evolucao[df_evolucao['Tema'].isin(temas_sel)].sort_values('Ano'), x='Ano',
                              y='Relevancia_Media_Anual', color='Tema', markers=True, color_discrete_map=mapa_cores,
                              template="plotly_white")
            fig_evo.update_xaxes(type='category', tickangle=-45)
            fig_evo.update_layout(
                legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5, font=dict(size=13)),
                margin=dict(l=20, r=20, t=30, b=100))
            st.plotly_chart(fig_evo, use_container_width=True)

            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📋 Contagem de Reuniões por Tema")

                # 1. Mantemos a SUA lógica original de filtragem (df_debatidos), só mudando 'Qtd' para 'Quantidade'
                contagem = df_debatidos[df_debatidos['Ano'].astype(str).isin(anos_sel)].groupby('Tema')[
                    'Arquivo'].nunique().reset_index(
                    name='Quantidade').sort_values('Quantidade')

                contagem['Cor'] = contagem['Tema'].apply(
                    lambda t: mapa_cores.get(t, '#EAEAEA') if t in temas_sel else '#EAEAEA')

                # 2. Atualizamos o X e o Text para puxarem a nova coluna 'Quantidade'
                fig_bar = px.bar(contagem, x='Quantidade', y='Tema', orientation='h', text='Quantidade',
                                 template="plotly_white", labels={'Quantidade': 'Reuniões', 'Tema': ''})

                fig_bar.update_traces(
                    marker_color=contagem['Cor'],
                    textposition='outside',
                    textangle=0,
                    cliponaxis=False
                )

                fig_bar.update_layout(
                    showlegend=False,
                    height=450,
                    margin=dict(l=0, r=40, t=20, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            with c2:
                st.subheader("☁️ Nuvem de Palavras")
                top_p = df_palavras[
                    ~df_palavras['Palavra'].str.lower().isin(['conselheiro', 'conselho', 'representante'])].groupby(
                    ['Palavra', 'Tema'])['Vezes_Ativada'].sum().reset_index()
                if not top_p.empty:
                    freq_dict = dict(zip(top_p['Palavra'], top_p['Vezes_Ativada']))
                    tema_pal = \
                    top_p.sort_values('Vezes_Ativada', ascending=False).drop_duplicates('Palavra').set_index('Palavra')[
                        'Tema'].to_dict()
                    x, y = np.ogrid[:450, :800]
                    mask = ((x - 225) ** 2 / (210 ** 2) + (y - 400) ** 2 / (380 ** 2) > 1).astype(int) * 255
                    wc = WordCloud(width=800, height=450, background_color=None, mode="RGBA", mask=mask, margin=10,
                                   max_words=120, min_font_size=10, max_font_size=60,
                                   color_func=lambda w, **k: mapa_cores.get(tema_pal.get(w), "#333333") if tema_pal.get(
                                       w) in temas_sel else "#EAEAEA").generate_from_frequencies(freq_dict)
                    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='none');
                    ax.imshow(wc, interpolation='bilinear');
                    ax.axis('off')
                    st.pyplot(fig, clear_figure=True, transparent=True)
    except Exception as e:
        st.warning(f"Dados indisponíveis: {e}")

# ==============================================================================
# ABA 3: FREQUÊNCIA E ENGAJAMENTO HISTÓRICO (Com Inteligência Temporal)
# ==============================================================================
with tab_frequencia:
    st.markdown("## 👥 Frequência e Engajamento Histórico")

    caminho_relatorio = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "Relatorio_Cadeiras_Absenteismo.xlsx")
    caminho_catalogo = os.path.join(config_ambiente.CAMINHO_RELATORIOS, "Catálogo_de_Metadados_CMTT.xlsx")

    try:
        # 1. Carregamento e Filtro
        df_cadeiras = pd.read_excel(caminho_relatorio)
        df_cadeiras = df_cadeiras[
            ~df_cadeiras['Segmento'].str.contains('SECRETARIA EXECUTIVA|CONVIDADO', case=False, na=False)]
        df_cadeiras['Presenca_Perc'] = (df_cadeiras['Pres'] / df_cadeiras['Total'] * 100).round(1).fillna(0)

        # 2. Catálogo (Extração de Ciclo de Vida: Criação/Extinção)
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            with st.expander("📚 CONTEXTO: Catálogo de Nomenclaturas (Nomes Reais)", expanded=False):
                try:
                    df_cat_full = pd.read_excel(caminho_catalogo, sheet_name=None)
                    aba_alvo = 'Evolução_das_Secretarias' if 'Evolução_das_Secretarias' in df_cat_full else \
                    list(df_cat_full.keys())[0]
                    df_cat = df_cat_full[aba_alvo]
                    df_cat = df_cat[
                        ~df_cat['Segmento'].str.contains('SECRETARIA EXECUTIVA|CONVIDADO', case=False, na=False)]
                    st.dataframe(df_cat, use_container_width=True, hide_index=True)

                    dict_historico = {}
                    dict_vida = {}
                    for _, row in df_cat.iterrows():
                        cad_pad = str(row.get('Cadeira Padronizada', ''))
                        if not cad_pad or cad_pad == 'nan': continue

                        nomes_validos = []
                        anos_validos = []
                        ult_nome = ""
                        # Varre colunas de mandatos para achar nascimento e morte
                        for col in df_cat.columns[2:]:
                            val = str(row[col]).strip()
                            if val not in ['-', 'nan', 'NaN', 'None', '']:
                                ano_ref = str(col).split('_')[0][:4]
                                anos_validos.append(int(ano_ref))
                                if val != ult_nome:
                                    nomes_validos.append(f"<b>{ano_ref}:</b> {val}")
                                    ult_nome = val

                        # Inteligência de Período de Existência
                        nascimento = min(anos_validos) if anos_validos else "N/A"
                        status = "Ativa" if max(anos_validos) >= 2024 else f"Extinta em {max(anos_validos)}"
                        dict_vida[cad_pad] = f"{nascimento} — {status}"
                        dict_historico[cad_pad] = "<br>".join(nomes_validos) if nomes_validos else "Sem histórico."
                except:
                    dict_historico, dict_vida = {}, {}; st.info("Catálogo indisponível.")

        with col_c2:
            try:
                with open(caminho_catalogo, "rb") as f_cat:
                    st.download_button(label="💾 Baixar Catálogo (Excel)", data=f_cat,
                                       file_name="Catalogo_Metadados_CMTT.xlsx", use_container_width=True)
            except:
                st.button("Download Indisponível", disabled=True)

        st.write("---")

        # 3. Processamento Temporal por Segmento
        reuniao_cols = [c for c in df_cadeiras.columns if re.search(r'\d{4}-\d{2}-\d{2}', str(c))]
        df_long = df_cadeiras.melt(id_vars=['Cadeira', 'Segmento'], value_vars=reuniao_cols, var_name='Reuniao',
                                   value_name='Status')
        df_long = df_long[df_long['Status'].isin(['Presente', 'Falta'])]
        df_long['Presenca_Num'] = (df_long['Status'] == 'Presente').astype(int)
        df_long['Ano'] = df_long['Reuniao'].str.extract(r'(\d{4})')

        # Mapeamento Amigável
        map_seg = lambda s: 'Poder Público' if 'ÓRGÃOS MUNICIPAIS' in str(s).upper() else (
            'Sociedade Civil' if 'SOCIEDADE CIVIL' in str(s).upper() else 'Operadores')
        df_long['Seg_Amigo'] = df_long['Segmento'].apply(map_seg)
        df_cadeiras['Seg_Amigo'] = df_cadeiras['Segmento'].apply(map_seg)

        # Médias Temporais
        df_geral = df_long.groupby('Ano')['Presenca_Num'].mean().mul(100).round(1).reset_index(name='Perc')
        df_geral['Seg_Amigo'] = 'Assiduidade Geral'
        df_seg_temp = df_long.groupby(['Ano', 'Seg_Amigo'])['Presenca_Num'].mean().mul(100).round(1).reset_index(
            name='Perc')
        df_temporal = pd.concat([df_geral, df_seg_temp])

        # 4. Interface de Filtros
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            seg_sel = st.multiselect("🎯 Filtrar Segmento:", options=sorted(df_cadeiras['Seg_Amigo'].unique()),
                                     default=sorted(df_cadeiras['Seg_Amigo'].unique()))
        with col_f2:
            cad_sel = st.multiselect("🪑 Analisar Cadeira(s) Específica(s):", options=sorted(
                df_cadeiras[df_cadeiras['Seg_Amigo'].isin(seg_sel)]['Cadeira'].unique()), default=[],
                                     placeholder="Todas do segmento")

        # 5. Gráfico de Linhas (Evolução Temporal)
        st.subheader("📈 Assiduidade Histórica nas Reuniões Plenárias")
        segs_plot = ['Assiduidade Geral'] + seg_sel
        fig_at = px.line(df_temporal[df_temporal['Seg_Amigo'].isin(segs_plot)].sort_values('Ano'), x='Ano', y='Perc',
                         color='Seg_Amigo', markers=True,
                         color_discrete_map={'Assiduidade Geral': '#2C3E50', 'Poder Público': '#2E4D68',
                                             'Sociedade Civil': '#11caa0', 'Operadores': '#D4AF37'},
                         template="plotly_white")
        fig_at.update_xaxes(type='category', categoryorder='array', categoryarray=sorted(df_temporal['Ano'].unique()))
        fig_at.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, title=""),
                             yaxis=dict(range=[0, 105], title="Presença %"), margin=dict(l=10, r=10, t=10, b=80))
        st.plotly_chart(fig_at, use_container_width=True)

        st.write("---")

        # 6. Gráfico de Barras (Ordem Alfabética + Período de Vida)
        st.subheader("🏛️ Participação por Cadeira (Ordem Alfabética)")
        df_bar = df_cadeiras[df_cadeiras['Seg_Amigo'].isin(seg_sel)].copy()
        if cad_sel: df_bar = df_bar[df_bar['Cadeira'].isin(cad_sel)]

        if not df_bar.empty:
            df_bar = df_bar.sort_values('Cadeira', ascending=False)
            df_bar['Hist'] = df_bar['Cadeira'].map(dict_historico).fillna("Sem histórico.")
            df_bar['Vida'] = df_bar['Cadeira'].map(dict_vida).fillna("Período não mapeado.")

            # Tooltip com texto solicitado e Período de Existência
            fig_bar = px.bar(df_bar, x='Presenca_Perc', y='Cadeira', orientation='h', text='Presenca_Perc',
                             color='Seg_Amigo',
                             color_discrete_map={'Poder Público': '#2E4D68', 'Sociedade Civil': '#11caa0',
                                                 'Operadores': '#D4AF37'}, custom_data=['Hist', 'Seg_Amigo', 'Vida'])
            fig_bar.update_traces(texttemplate='%{text}%', textposition='outside',
                                  hovertemplate="<b>%{y}</b> (%{customdata[1]})<br>Assiduidade Histórica Global: %{x}%<br><b>Período:</b> %{customdata[2]}<br><br><b>Histórico (ver Catálogo de Nomenclaturas e Mandatos):</b><br>%{customdata[0]}<extra></extra>")
            # --- Ativação do Balão e Correção do Balão Torto ---
            fig_bar.update_layout(
                hovermode='closest',  # <--- Volta para o padrão seguro que não gira o balão
                hoverlabel=dict(align="left"),  # <--- Força o texto dentro do balão a ficar retinho
                showlegend=False,
                xaxis=dict(range=[-2, 115], title="Presença (%)"),
                # <--- O TRUQUE: -2 cria a "área invisível" para o mouse achar o 0%
                yaxis_title="",
                height=max(300, len(df_bar) * 45),
                margin=dict(l=0, r=40, t=10, b=20)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("👆 Selecione um segmento para visualizar.")

    except Exception as e:
        st.error(f"Erro ao processar frequência: {e}")