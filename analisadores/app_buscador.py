import sys
import os
import re
import json
import shutil
import base64
import pandas as pd
import streamlit as st

# --- Configuração de Caminhos ---
DIR_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(DIR_BASE)
from extratores.gerenciador_io import ler_texto_pdf, carregar_index_atas

CAMINHO_CACHE = os.path.join(DIR_BASE, 'dados', 'configs', '.cache_corpus_atas.json')
CAMINHO_BASE_MANDATOS = os.path.join(DIR_BASE, 'dados', 'base_dados', 'base_mandatosCMTT.xlsx')
CAMINHO_INDEX_EXCEL = os.path.join(DIR_BASE, 'dados', 'base_dados', 'index_atasCMTT.xlsx')

# --- Configuração da Página ---
st.set_page_config(page_title="BuscaCMTT", layout="wide", initial_sidebar_state="collapsed")

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


def construir_cache_novo():
    dados_index = carregar_index_atas()
    if not dados_index:
        st.error("❌ Índice oficial não encontrado.")
        return False

    lista_arquivos = []
    if isinstance(dados_index, dict):
        for chave, metadados in dados_index.items():
            item = metadados.copy() if isinstance(metadados, dict) else {}
            if 'arquivo' not in item: item['arquivo'] = chave
            lista_arquivos.append(item)
    else:
        lista_arquivos = dados_index

    corpus_cache = []
    texto_progresso = st.empty()
    barra_progresso = st.progress(0)

    for i, item in enumerate(lista_arquivos):
        arquivo = item.get('arquivo') or item.get('caminho')
        if arquivo:
            nome_arq = os.path.basename(arquivo)
            texto_progresso.text(f"Processando: {nome_arq}...")

            linhas = ler_texto_pdf(arquivo)
            if linhas:
                data_doc = item.get('data') or item.get('Data') or "N/A"
                if data_doc == "N/A":
                    ano_match = re.search(r'20\d{2}', nome_arq)
                    data_doc = ano_match.group() if ano_match else "N/A"

                corpus_cache.append({
                    "Fonte": nome_arq,
                    "Data": data_doc,
                    "Reunião": item.get('nome_reuniao') or item.get('reuniao') or "Ata de Reunião",
                    "Linhas": linhas
                })
        barra_progresso.progress((i + 1) / len(lista_arquivos))

    with open(CAMINHO_CACHE, 'w', encoding='utf-8') as f:
        json.dump(corpus_cache, f, ensure_ascii=False, indent=2)

    texto_progresso.empty()
    barra_progresso.empty()
    carregar_corpus_memoria.clear()
    return True


# --- NOVIDADE: O Olho de Hórus do Arquivo (Carimbos de Tempo) ---
def get_carimbo_tempo(caminho):
    """Lê a data/hora exata da última modificação do arquivo no sistema."""
    return os.path.getmtime(caminho) if os.path.exists(caminho) else 0


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria(carimbo_cache):
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
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

if senha_admin == "cmtt2013":
    st.sidebar.warning("Modo Administrador Ativo")
    if st.sidebar.button("🔄 Reconstruir Cache (Geral)"):
        st.cache_data.clear()
        with st.spinner("Lendo PDFs e extraindo metadados..."):
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

caminho_logo_pref = os.path.join(DIR_BASE, 'dados', 'configs', 'logo_prefeitura.png')
caminho_logo_cmtt = os.path.join(DIR_BASE, 'dados', 'configs', 'logo_cmtt.jpg')

try:
    with open(caminho_logo_pref, "rb") as img1, open(caminho_logo_cmtt, "rb") as img2:
        b64_pref = base64.b64encode(img1.read()).decode()
        b64_cmtt = base64.b64encode(img2.read()).decode()

        html_cabecalho = f"""
        <div style="display: flex; justify-content: center; margin-bottom: 2rem; margin-top: 1rem;">
            <div style="background-color: white; padding: 15px 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 30px; max-width: 95%;">
                <img src="data:image/png;base64,{b64_pref}" style="height: 100px; width: auto; max-width: 100%; object-fit: contain;">
                <img src="data:image/jpeg;base64,{b64_cmtt}" style="height: 70px; width: auto; max-width: 100%; object-fit: contain;">
            </div>
        </div>
        """
        st.markdown(html_cabecalho, unsafe_allow_html=True)
except Exception as e:
    st.warning("⚠️ Não foi possível carregar os logos no cabeçalho. Verifique os nomes dos arquivos.")

st.write("---")

# 2. Miolo da Busca
_, col_miolo, _ = st.columns([1, 6, 1])

with col_miolo:
    st.markdown(
        "<h3 style='text-align: center; color: #2C3E50; margin-bottom: 25px;'>🔍 Digite para buscar nas bases do CMTT</h3>",
        unsafe_allow_html=True)

    # --- A MÁGICA DOS CARIMBOS DE TEMPO AQUI ---
    # Captura a hora exata em que os arquivos foram alterados pela última vez
    carimbo_cache = get_carimbo_tempo(CAMINHO_CACHE)
    carimbo_mandatos = get_carimbo_tempo(CAMINHO_BASE_MANDATOS)
    carimbo_index = get_carimbo_tempo(CAMINHO_INDEX_EXCEL)

    # O Streamlit agora compara a hora. Se for mais recente, ele lê tudo de novo sozinho!
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
            usuario = "giselehbarbosa-dev"
            repo = "CodigoCMTT"
            branch = "main"

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
        nome_arquivo_csv = f"busca_CMTT_{termo.replace(' ', '_')}_{data_hoje}.csv"

        st.download_button(
            label="📊 Baixar Tabela de Resultados (CSV)",
            data=csv_bytes,
            file_name=nome_arquivo_csv,
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning(f"∅ Nada encontrado para o termo '{termo}'.")