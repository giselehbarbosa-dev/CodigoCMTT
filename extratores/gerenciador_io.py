import os
import re
import json
import pdfplumber
from datetime import datetime
from extratores.config_filtros import converter_periodo_em_datas

# 1. O GPS MÁGICO (Descobre automaticamente a pasta raiz do projeto)
# Como este arquivo está dentro da pasta 'extratores', mandamos ele voltar uma pasta para achar a raiz (Codigo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Caminhos relativos e dinâmicos (Funcionam no PC, no Mac, no Linux e na Nuvem!)
CAMINHO_CONFIGS = os.path.join(BASE_DIR, "dados", "configs")
CAMINHO_INDEX_JSON = os.path.join(CAMINHO_CONFIGS, "index_atas.json")

# 3. Caminho dos PDFs acompanhando a sua organização de pastas
# Assumindo que você colocou a pasta de PDFs dentro de dados/base_dados/ como mostrou na foto
CAMINHO_PDFS_PADRAO = os.path.join(BASE_DIR, "dados", "base_dados", "pdf_atas_pleno")

def verificar_pastas():
    if not os.path.exists(CAMINHO_CONFIGS):
        print(f"❌ Erro: Pasta de configs não encontrada em {CAMINHO_CONFIGS}")
        return False
    return True

def carregar_index_atas():
    if not os.path.exists(CAMINHO_INDEX_JSON):
        return {}
    with open(CAMINHO_INDEX_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def carregar_bases_mandatos():
    mandatos = []
    if not os.path.exists(CAMINHO_CONFIGS): return []
    for arq in os.listdir(CAMINHO_CONFIGS):
        if arq.endswith('.json') and 'index_atas' not in arq:
            ini, fim = converter_periodo_em_datas(arq)
            if ini != datetime.min:
                try:
                    with open(os.path.join(CAMINHO_CONFIGS, arq), 'r', encoding='utf-8') as f:
                        mandatos.append({"inicio": ini, "fim": fim, "arquivo": arq, "dados": json.load(f)})
                except Exception as e:
                    print(f"⚠️ Erro ao ler mandato {arq}: {e}")
    return mandatos

def ler_texto_pdf(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        caminho_arquivo = os.path.join(CAMINHO_PDFS_PADRAO, os.path.basename(caminho_arquivo))
        if not os.path.exists(caminho_arquivo):
            return []
    linhas_orig = []
    try:
        with pdfplumber.open(caminho_arquivo) as pdf:
            for p in pdf.pages:
                txt = p.extract_text() or ""
                txt = txt.replace('\r', '')
                for linha in txt.split('\n'):
                    l = linha.strip()
                    l = re.sub(r'\s+', ' ', l)
                    if len(l) > 3:
                        linhas_orig.append(l)
    except Exception as e:
        print(f"⚠️ Erro leitura PDF {os.path.basename(caminho_arquivo)}: {e}")
    return linhas_orig