"""
=============================================================================
🏛️ Projeto CMTT - Mineração e Análise de Dados
Script: motores/motor_tematico.py
Objetivo: Fase 4 - Mineração Temática e Extração de OSCs usando o Cache JSON
=============================================================================
"""

import os
import sys
import json
import pandas as pd
import re
from tqdm import tqdm

# Garante a importação dos módulos do core e utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import config_ambiente
from utils.config_filtros import normalizar
from utils.ferramentas_matcher import PREFIXOS_BLOQUEIO, TERMOS_EXATOS

# Carregamento seguro do spaCy para extração de entidades (NER)
try:
    import spacy
    nlp = spacy.load("pt_core_news_sm")
except (ImportError, OSError):
    print("⚠️ ERRO: Execute 'pip install spacy' e 'python -m spacy download pt_core_news_sm'")
    sys.exit()

# ==========================================
# 1. FUNÇÕES DE BLINDAGEM E EXTRAÇÃO
# ==========================================

def criar_escudo_de_nomes():
    """Cria lista de exclusão baseada nas presenças confirmadas da Fase 1."""
    escudo = set()
    for caminho in [config_ambiente.CAMINHO_CSV_PRESENCA, config_ambiente.CAMINHO_CSV_VISITANTES]:
        if os.path.exists(caminho):
            df = pd.read_csv(caminho, sep=';', encoding='utf-8-sig')
            coluna = 'Nome' if 'presenca' in caminho else 'Nome_na_Ata'
            for n in df[coluna].dropna().unique():
                if str(n).upper() != "VAGO": escudo.add(normalizar(str(n)))
    return escudo

def extrair_entidades_e_temas(texto_frase, escudo):
    """Aplica o dicionário temático e identifica OSCs ignorando o escudo de pessoas."""
    texto_norm = normalizar(texto_frase)
    temas_encontrados = []

    # 1. Busca Temática Dinâmica (Lê do config_ambiente)
    for categoria, regex_lista in config_ambiente.DICIONARIO_TEMAS.items():
        for padrao in regex_lista:
            if re.search(padrao, texto_norm, re.IGNORECASE):
                temas_encontrados.append(categoria)
                break # Achou um termo da categoria, pula para a próxima categoria

    # 2. Extração de OSCs (IA) com Filtros Rigorosos
    oscs_encontradas = []
    doc = nlp(texto_frase)
    for ent in doc.ents:
        if ent.label_ in ["ORG", "LOC"]:
            ent_norm = normalizar(ent.text)

            # Filtro de tamanho e Extração Inversa (O Escudo)
            if len(ent_norm) < 3 or ent_norm in escudo: continue

            # Bloqueio de termos institucionais comuns (Evita capturar "Prefeitura")
            if any(ent_norm.startswith(p) for p in PREFIXOS_BLOQUEIO) or ent_norm in TERMOS_EXATOS:
                continue

            oscs_encontradas.append(ent.text.strip(" ,.;:-\"\'"))

    return list(set(temas_encontrados)), list(set(oscs_encontradas))

# ==========================================
# 2. O MAESTRO DA EXECUÇÃO
# ==========================================

def executar_tematico():
    print("🛡️ MOTOR TEMÁTICO E OSC V51 (DESACOPLADO E PARTICIONADO) 🛡️")

    # Valida se o cache existe
    if not os.path.exists(config_ambiente.CAMINHO_CACHE_BUSCADOR):
        print("❌ Cache não encontrado! Rode o construtor_cache.py ou o app_buscador.py primeiro.")
        return

    print("⏳ Carregando cérebro de textos...")
    with open(config_ambiente.CAMINHO_CACHE_BUSCADOR, 'r', encoding='utf-8') as f:
        corpus_cache = json.load(f)

    escudo = criar_escudo_de_nomes()
    res_temas, res_oscs = [], []

    # 🆕 NOVA LÓGICA: Achata as prateleiras do cache para uma única lista
    documentos_para_processar = []
    if isinstance(corpus_cache, dict):
        for lista_docs in corpus_cache.values():
            documentos_para_processar.extend(lista_docs)
    else:
        documentos_para_processar = corpus_cache

    for documento in tqdm(documentos_para_processar, desc="Aplicando Inteligência (Temas e OSCs)"):
        pdf_nome = documento.get("Fonte", "Desconhecido")
        reuniao = documento.get("Reunião", "N/A")
        data_bruta = documento.get("Data", "N/A")

        # Formata a data para AAAA/MM para facilitar dashboards
        try:
            data_ref = pd.to_datetime(data_bruta, format="%d/%m/%Y").strftime("%Y/%m")
        except:
            data_ref = data_bruta

        # Pega as linhas prontas do cache e junta para a IA ler
        texto_ata = " ".join(documento.get("Linhas", []))
        frases = re.split(r'(?<=[.!?]) +', texto_ata)

        for frase in frases:
            if len(frase) < 25: continue # Pula lixo visual curto

            temas, oscs = extrair_entidades_e_temas(frase, escudo)

            for t in temas:
                res_temas.append({
                    "Reuniao": reuniao, "Data (AAAA/MM)": data_ref,
                    "Arquivo": pdf_nome, "Trecho_na_Ata": frase.strip(), "Tema_Classificado": t
                })
            for o in oscs:
                res_oscs.append({
                    "Reuniao": reuniao, "Data (AAAA/MM)": data_ref,
                    "Arquivo": pdf_nome, "OSC_Encontrada": o, "Contexto": frase.strip()
                })

    # ==========================================
    # 3. EXPORTAÇÃO DOS PRODUTOS
    # ==========================================
    print("\n💾 Consolidando arquivos...")
    os.makedirs(config_ambiente.CAMINHO_PROCESSADOS, exist_ok=True)

    for dados, nome_arq in [(res_temas, "temas_debatidos.csv"), (res_oscs, "oscs_identificadas.csv")]:
        if dados:
            df = pd.DataFrame(dados).drop_duplicates()
            caminho = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, nome_arq)
            df.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
            print(f"✅ {len(df)} registros salvos em {nome_arq}")
        else:
            print(f"⚠️ Nenhum dado encontrado para gerar {nome_arq}")

if __name__ == "__main__":
    executar_tematico()