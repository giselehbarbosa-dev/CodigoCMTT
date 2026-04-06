import sys
import os
import re
import json
import shutil
import base64
import pandas as pd
import streamlit as st

# O Streamlit às vezes perde a raiz do projeto, então garantimos que ele ache a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas

# 🆕 A ÚNICA MUDANÇA: Importamos o construtor centralizado de cache!
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
            # 🆕 Se for o cache particionado (dicionário), achata para o buscador varrer tudo
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

        # 🆕 Ajuste leve: como removemos a função interna, usamos o spinner nativo do Streamlit
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

# --- Área Principal ---

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

# 2. Miolo da Busca
_, col_miolo, _ = st.columns([1, 6, 1])

with col_miolo:
    st.markdown(
        f"<h3 style='text-align: center; color: #2C3E50; margin-bottom: 25px;'>🔍 Digite para buscar nas bases do {sigla_conselho}</h3>",
        unsafe_allow_html=True)

    # --- A MÁGICA DOS CARIMBOS DE TEMPO AQUI ---
    carimbo_cache = get_carimbo_tempo(CAMINHO_CACHE)
    carimbo_mandatos = get_carimbo_tempo(CAMINHO_BASE_MANDATOS)
    carimbo_index = get_carimbo_tempo(CAMINHO_INDEX_EXCEL)

    corpus_completo = carregar_corpus_memoria(carimbo_cache) + carregar_fontes_extras(carimbo_mandatos, carimbo_index)

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
            # Puxando dinamicamente do config_ambiente!
            usuario = config_ambiente.GITHUB_USER
            repo = config_ambiente.GITHUB_REPO
            branch = config_ambiente.GITHUB_BRANCH

            if nome_arquivo.endswith('.pdf'):
                return f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/pdf_atas_pleno/{nome_arquivo}"
            elif nome_arquivo.endswith('.xlsx'):
                return f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/{nome_arquivo}"
            return ""


        # --- A) PREPARANDO A TABELA PARA O CSV (Limpa e com coluna de Link Original) ---
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

        # Exibe a tabela na tela renderizando o HTML sem quebrar o CSV depois
        tabela_html = df_tela.to_html(escape=False, index=False, classes="tabela-resultados")
        st.write(tabela_html, unsafe_allow_html=True)

        st.write("---")

        # Botão de download usando o df_csv (Limpíssimo para Excel)
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