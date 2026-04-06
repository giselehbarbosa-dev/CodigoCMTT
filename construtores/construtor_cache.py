"""
=============================================================================
🏛️ Projeto CMTT - Mineração e Análise de Dados
Script: construtores/construtor_cache.py
Objetivo: Lê os PDFs e gera o .cache_corpus_atas.json (Com Carga Incremental)
=============================================================================
"""

import sys
import os
import re
import json

# Garante que o Python encontra a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas

def construir_cache_novo(callback_progresso=None, callback_texto=None, forcar_completo=False):
    """
    Constrói ou atualiza o cache de textos dos PDFs.
    Se forcar_completo=False, faz carga incremental (apenas PDFs novos).
    """
    dados_index = carregar_index_atas()
    if not dados_index:
        msg = "❌ Índice oficial não encontrado."
        if callback_texto: callback_texto(msg)
        else: print(msg)
        return False

    caminho_cache = config_ambiente.CAMINHO_CACHE_BUSCADOR
    corpus_cache = []
    arquivos_ja_processados = set()

    # ==========================================
    # 1. LÓGICA INCREMENTAL (Descobre quem já foi lido)
    # ==========================================
    if not forcar_completo and os.path.exists(caminho_cache):
        try:
            with open(caminho_cache, 'r', encoding='utf-8') as f:
                corpus_cache = json.load(f)
            # Anota o nome de todos os PDFs que já estão no cache
            for doc in corpus_cache:
                arquivos_ja_processados.add(doc.get("Fonte"))

            msg_inc = f"⚡ Modo Incremental: {len(arquivos_ja_processados)} documentos já estão no cache."
            if callback_texto: callback_texto(msg_inc)
            else: print(msg_inc)
        except Exception as e:
            print(f"⚠️ Erro ao ler cache existente: {e}. Recriando do zero.")

    # ==========================================
    # 2. PREPARAÇÃO E FILTRAGEM
    # ==========================================
    lista_arquivos = []
    if isinstance(dados_index, dict):
        for chave, metadados in dados_index.items():
            item = metadados.copy() if isinstance(metadados, dict) else {}
            if 'arquivo' not in item and 'caminho' not in item:
                item['arquivo'] = chave
            lista_arquivos.append(item)
    else:
        lista_arquivos = dados_index

    # Filtra: Só deixa na fila quem NÃO está no conjunto de 'arquivos_ja_processados'
    arquivos_para_processar = []
    for item in lista_arquivos:
        arquivo = item.get('arquivo') or item.get('caminho')
        if arquivo:
            nome_arq = os.path.basename(arquivo)
            if nome_arq not in arquivos_ja_processados:
                arquivos_para_processar.append(item)

    total_arquivos = len(arquivos_para_processar)

    if total_arquivos == 0:
        msg = "✅ Cache já está 100% atualizado! Nenhum PDF novo encontrado."
        if callback_texto: callback_texto(msg)
        else: print(msg)
        return True

    msg_inicio = f"🔎 Extraindo texto de {total_arquivos} NOVOS documentos..."
    if callback_texto: callback_texto(msg_inicio)
    else: print(msg_inicio)

    # ==========================================
    # 3. EXTRAÇÃO (Apenas os novos)
    # ==========================================
    for i, item in enumerate(arquivos_para_processar):
        arquivo = item.get('arquivo') or item.get('caminho')
        nome_arq = os.path.basename(arquivo)

        if callback_texto: callback_texto(f"Lendo: {nome_arq}...")
        else: print(f"   Lendo: {nome_arq}...")

        linhas = ler_texto_pdf(arquivo)

        if linhas:
            data_doc = item.get('dados') or item.get('Data') or "N/A"
            if data_doc == "N/A":
                ano_match = re.search(r'20\d{2}', nome_arq)
                data_doc = ano_match.group() if ano_match else "N/A"

            # Adiciona o novo PDF à lista gigante existente
            corpus_cache.append({
                "Fonte": nome_arq,
                "Data": data_doc,
                "Reunião": item.get('nome_reuniao') or item.get('reuniao') or item.get('titulo_reuniao') or "Ata de Reunião",
                "Linhas": linhas
            })

        if callback_progresso:
            callback_progresso((i + 1) / total_arquivos)

    # ==========================================
    # 4. SALVAMENTO (Sobrescreve com os dados anexados)
    # ==========================================
    os.makedirs(os.path.dirname(caminho_cache), exist_ok=True)
    with open(caminho_cache, 'w', encoding='utf-8') as f:
        json.dump(corpus_cache, f, ensure_ascii=False, indent=2)

    msg_sucesso = f"✅ Cache salvo com sucesso! O banco agora tem {len(corpus_cache)} atas."
    if callback_texto: callback_texto(msg_sucesso)
    else: print(f"\n{msg_sucesso}")

    return True

if __name__ == "__main__":
    print("🚀 Iniciando Construtor de Cache...")
    # Ao rodar pelo terminal, ele tenta incremental por padrão.
    # Se quiser forçar do zero, mude para: construir_cache_novo(forcar_completo=True)
    construir_cache_novo(forcar_completo=False)