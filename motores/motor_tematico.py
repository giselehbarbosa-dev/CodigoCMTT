"""
=============================================================================
🏛️ Projeto CMTT - Mineração e Análise de Dados
Script: motores/motor_tematico.py
Objetivo: Fase 4 - Mineração Temática com Frequência e Auditoria XAI (Palavras)
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

def extrair_temas_e_palavras(texto_frase):
    """
    Aplica o dicionário temático e retorna não só o tema,
    mas a palavra exata que ativou a regra.
    """
    texto_norm = normalizar(texto_frase)
    temas_encontrados = {}

    for categoria, regex_lista in config_ambiente.DICIONARIO_TEMAS.items():
        for padrao in regex_lista:
            # \b garante que o match ocorra apenas no INÍCIO de uma palavra.
            padrao_rigido = rf"\b{padrao}"
            match = re.search(padrao_rigido, texto_norm, re.IGNORECASE)

            if match:
                # Se achou, pega a palavra exata que o robô leu no texto
                palavra_gatilho = match.group(0).lower()
                temas_encontrados[categoria] = palavra_gatilho
                break # Para a contagem desta categoria nesta frase (mantém a estatística)

    return temas_encontrados

def executar_tematico():
    print("🛡️ MOTOR TEMÁTICO V62 (TERMÔMETRO + AUDITORIA DE PALAVRAS) 🛡️")

    if not os.path.exists(config_ambiente.CAMINHO_CACHE_BUSCADOR):
        print("❌ Cache não encontrado! Rode o construtor_cache.py primeiro.")
        return

    print("⏳ Carregando cérebro de textos...")
    with open(config_ambiente.CAMINHO_CACHE_BUSCADOR, 'r', encoding='utf-8') as f:
        corpus_cache = json.load(f)

    res_temas = []

    # Achata as prateleiras do cache para uma única lista de documentos
    documentos_para_processar = []
    if isinstance(corpus_cache, dict):
        for lista_docs in corpus_cache.values():
            documentos_para_processar.extend(lista_docs)
    else:
        documentos_para_processar = corpus_cache

    # ==========================================
    # LÓGICA DE DOCUMENTO (Com rastreio de palavras)
    # ==========================================
    for documento in tqdm(documentos_para_processar, desc="Analisando Relevância de Pautas"):
        pdf_nome = documento.get("Fonte", "Desconhecido")
        reuniao = documento.get("Reunião", "N/A")
        data_bruta = documento.get("Data", "N/A")

        try:
            data_ref = pd.to_datetime(data_bruta, format="%d/%m/%Y").strftime("%Y/%m")
        except:
            data_ref = data_bruta

        texto_ata = " ".join(documento.get("Linhas", []))
        frases = re.split(r'(?<=[.!?]) +', texto_ata)

        # O placar agora tem uma 'cestinha' (set) para guardar as palavras que encontrou
        placar_ata = {cat: {"ocorrencias": 0, "exemplos": [], "palavras_encontradas": set()} for cat in config_ambiente.DICIONARIO_TEMAS.keys()}
        total_hits_ata = 0

        # Varrer as frases e alimentar o placar da ata
        for frase in frases:
            if len(frase) < 40:
                continue

            temas_na_frase = extrair_temas_e_palavras(frase)

            for tema, palavra in temas_na_frase.items():
                placar_ata[tema]["ocorrencias"] += 1
                total_hits_ata += 1

                # Guarda a palavra que serviu de gatilho
                placar_ata[tema]["palavras_encontradas"].add(palavra)

                # Guarda apenas as 2 primeiras frases como prova documental
                if len(placar_ata[tema]["exemplos"]) < 2:
                    placar_ata[tema]["exemplos"].append(frase.strip())

        # ==========================================
        # FILTRO DE RUÍDO E SALVAMENTO
        # ==========================================
        if total_hits_ata == 0:
            continue

        for tema, dados in placar_ata.items():
            ocorrencias = dados["ocorrencias"]

            if ocorrencias > 0:
                relevancia_percentual = (ocorrencias / total_hits_ata) * 100

                # Só considera "Pauta da Reunião" se representou pelo menos 5% do debate
                # E se a palavra apareceu pelo menos 2 vezes
                if relevancia_percentual >= 5.0 and ocorrencias >= 2:

                    contexto_prova = " [...] ".join(dados["exemplos"])

                    # Junta as palavras-chave encontradas numa string bonitinha
                    palavras_str = ", ".join(sorted(list(dados["palavras_encontradas"])))

                    res_temas.append({
                        "Arquivo": pdf_nome,
                        "Reuniao": reuniao,
                        "Data (AAAA/MM)": data_ref,
                        "Tema_Classificado": tema,
                        "Ocorrencias": ocorrencias,
                        "Relevancia_(%)": round(relevancia_percentual, 1),
                        "Palavras_Chave_Ativadas": palavras_str, # <--- A NOVA COLUNA AQUI!
                        "Trecho_Prova_(Auditoria)": contexto_prova
                    })

    # ==========================================
    # EXPORTAÇÃO DOS PRODUTOS
    # ==========================================
    print("\n💾 Consolidando arquivos...")
    os.makedirs(config_ambiente.CAMINHO_PROCESSADOS, exist_ok=True)

    if res_temas:
        df = pd.DataFrame(res_temas)
        df = df.sort_values(by=["Arquivo", "Relevancia_(%)"], ascending=[True, False])

        caminho = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv")
        df.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
        print(f"✅ Arquivo salvo com sucesso! {len(df)} pautas principais identificadas no acervo.")
    else:
        print(f"⚠️ Nenhum tema principal alcançou o sarrafo de qualidade.")

if __name__ == "__main__":
    executar_tematico()