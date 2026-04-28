"""
=============================================================================
🏛️ Projeto CMTT - Mineração e Análise de Dados
Script: motores/motor_tematico.py
Objetivo: Fase 4 - Mineração Temática com Frequência Relativa (Termômetro)
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

def extrair_temas_fidelidade(texto_frase):
    """Aplica o dicionário temático com amarras rígidas de borda de palavra."""
    texto_norm = normalizar(texto_frase)
    temas_encontrados = []

    for categoria, regex_lista in config_ambiente.DICIONARIO_TEMAS.items():
        for padrao in regex_lista:
            # \b garante que o match ocorra apenas no INÍCIO de uma palavra.
            padrao_rigido = rf"\b{padrao}"
            if re.search(padrao_rigido, texto_norm, re.IGNORECASE):
                temas_encontrados.append(categoria)
                break

    return list(set(temas_encontrados))

def executar_tematico():
    print("🛡️ MOTOR TEMÁTICO V61 (TERMÔMETRO DE RELEVÂNCIA) 🛡️")

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
    # LÓGICA DE DOCUMENTO (E não mais de linha)
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

        # Cria um placar vazio para esta Ata específica
        placar_ata = {cat: {"ocorrencias": 0, "exemplos": []} for cat in config_ambiente.DICIONARIO_TEMAS.keys()}
        total_hits_ata = 0

        # Varrer as frases e alimentar o placar da ata
        for frase in frases:
            if len(frase) < 40:
                continue

            temas_na_frase = extrair_temas_fidelidade(frase)

            for t in temas_na_frase:
                placar_ata[t]["ocorrencias"] += 1
                total_hits_ata += 1
                # Guarda apenas as 2 primeiras frases como prova documental (XAI)
                if len(placar_ata[t]["exemplos"]) < 2:
                    placar_ata[t]["exemplos"].append(frase.strip())

        # ==========================================
        # FILTRO DE RUÍDO E SALVAMENTO
        # ==========================================
        # Se a ata não teve nenhum tema do nosso dicionário, pula.
        if total_hits_ata == 0:
            continue

        for tema, dados in placar_ata.items():
            ocorrencias = dados["ocorrencias"]

            if ocorrencias > 0:
                relevancia_percentual = (ocorrencias / total_hits_ata) * 100

                # 🛑 O SARRAFO DE QUALIDADE:
                # Só considera "Pauta da Reunião" se representou pelo menos 5% do debate
                # E se a palavra apareceu pelo menos 2 vezes (evita palavras soltas acidentais)
                if relevancia_percentual >= 5.0 and ocorrencias >= 2:

                    # Junta as frases de exemplo bonitinhas para a coluna de auditoria
                    contexto_prova = " [...] ".join(dados["exemplos"])

                    res_temas.append({
                        "Arquivo": pdf_nome,
                        "Reuniao": reuniao,
                        "Data (AAAA/MM)": data_ref,
                        "Tema_Classificado": tema,
                        "Ocorrencias": ocorrencias,
                        "Relevancia_(%)": round(relevancia_percentual, 1),
                        "Trecho_Prova_(Auditoria)": contexto_prova
                    })

    # ==========================================
    # EXPORTAÇÃO DOS PRODUTOS
    # ==========================================
    print("\n💾 Consolidando arquivos...")
    os.makedirs(config_ambiente.CAMINHO_PROCESSADOS, exist_ok=True)

    if res_temas:
        # Ordena para ficar bonito no CSV (Por ata e depois por relevância do tema)
        df = pd.DataFrame(res_temas)
        df = df.sort_values(by=["Arquivo", "Relevancia_(%)"], ascending=[True, False])

        caminho = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv")
        df.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
        print(f"✅ Arquivo salvo com sucesso! {len(df)} pautas principais identificadas no acervo.")
    else:
        print(f"⚠️ Nenhum tema principal alcançou o sarrafo de qualidade.")

if __name__ == "__main__":
    executar_tematico()