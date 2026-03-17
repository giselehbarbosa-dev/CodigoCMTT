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

    /* CSS para deixar a tabela de resultados com cara de sistema profissional */
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


@st.cache_data(show_spinner=False)
def carregar_corpus_memoria():
    if os.path.exists(CAMINHO_CACHE):
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


@st.cache_data(show_spinner=False)
def carregar_fontes_extras():
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
        st.cache_data.clear()  # Limpa a memória do Streamlit
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

# 1. O Retângulo Branco com os Logos (Comportamento Flexível e Responsivo para Mobile)
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

    corpus_completo = carregar_corpus_memoria() + carregar_fontes_extras()

    if corpus_completo:
        termo = st.text_input("Busca Oculta", label_visibility="collapsed")
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
        for linha in doc["Linhas"]:
            if regex.search(linha):
                resultados.append({
                    "Fonte": doc.get("Fonte", "N/A"),
                    "Data": doc.get("Data", "N/A"),
                    "Reunião/Origem": doc.get("Reunião", "N/A"),
                    "Contexto": linha.strip()
                })

    if resultados:
        df_res = pd.DataFrame(resultados)
        st.success(f"Encontradas {len(df_res)} ocorrências!")


        # Função inteligente que gera link de download embutido para PDF ou Excel
        # Função nível Cloud: Cria links diretos para o GitHub (Zero consumo de memória)
        def linkar_fonte(fonte_str):
            nome_arquivo = fonte_str.split(" (Aba:")[0].strip()

            # --- PREENCHA COM OS SEUS DADOS DO GITHUB ---
            usuario = "giselehbarbosa-dev"
            repo = "CodigoCMTT"
            branch = "main"

            if nome_arquivo.endswith('.pdf'):
                # Cria o link direto para o PDF no GitHub
                url = f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/pdf_atas_pleno/{nome_arquivo}"
                return f'<a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none; font-weight: bold;">📕 {fonte_str}</a>'

            elif nome_arquivo.endswith('.xlsx'):
                # Cria o link direto para a Planilha no GitHub
                url = f"https://raw.githubusercontent.com/{usuario}/{repo}/{branch}/dados/base_dados/{nome_arquivo}"
                return f'<a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none; font-weight: bold;">📗 {fonte_str}</a>'

            return fonte_str  # Retorna normal se não reconhecer


        # Aplica a função de link na coluna Fonte
        df_res['Fonte'] = df_res['Fonte'].apply(linkar_fonte)

        # Exibe a tabela renderizando o HTML do link e aplicando nosso CSS customizado
        tabela_html = df_res.to_html(escape=False, index=False, classes="tabela-resultados")
        st.write(tabela_html, unsafe_allow_html=True)

        st.write("---")
        csv = df_res.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        data_hoje = pd.Timestamp.now().strftime("%Y-%m-%d")
        nome_arquivo_csv = f"busca_CMTT_{termo.replace(' ', '_')}_{data_hoje}.csv"

        st.download_button(
            label="📊 Baixar Tabela de Resultados (CSV)",
            data=csv,
            file_name=nome_arquivo_csv,
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning(f"∅ Nada encontrado para o termo '{termo}'.")