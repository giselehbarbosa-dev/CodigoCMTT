import sys
import os
import re
import json
import pandas as pd

# 1. Ajuste do Path para encontrar o gerenciador_io na pasta extratores
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from extratores.gerenciador_io import ler_texto_pdf, carregar_index_atas

# 2. Define onde o cache oculto será salvo
CAMINHO_CACHE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'dados', 'configs', '.cache_corpus_atas.json'))


def criar_padrao_flexivel(termo_busca):
    palavras = termo_busca.strip().split()
    if not palavras: return None
    padrao = r".*?".join([re.escape(p) for p in palavras])
    return re.compile(padrao, re.IGNORECASE)


def construir_ou_carregar_cache(forcar_atualizacao=False):
    # Se já existir e não for para forçar, carrega da memória rápido
    if not forcar_atualizacao and os.path.exists(CAMINHO_CACHE):
        print("⚡ Carregando dados do Cache rápido...")
        with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)

    print("⏳ Construindo o Cache pela primeira vez...")
    print("Isso PODE e DEVE demorar alguns minutos. Lendo PDFs...")

    dados_index = carregar_index_atas()
    if not dados_index:
        print("❌ Índice oficial não encontrado para gerar o cache.")
        return []

    # Adaptação para o formato do seu JSON
    lista_arquivos = []
    if isinstance(dados_index, dict):
        for chave, metadados in dados_index.items():
            item = metadados.copy() if isinstance(metadados, dict) else {}
            if 'caminho' not in item and 'arquivo' not in item:
                item['arquivo'] = chave
            lista_arquivos.append(item)
    else:
        lista_arquivos = dados_index

    corpus_cache = []
    print(f"🔎 Encontrados {len(lista_arquivos)} itens no índice. Iniciando extração...")

    # Faz a varredura abrindo os PDFs
    for item in lista_arquivos:
        caminho = item.get('caminho') or item.get('arquivo', '')

        if caminho:
            print(f"   Lendo: {caminho} ...")
            linhas_extraidas = ler_texto_pdf(caminho)

            if linhas_extraidas:
                corpus_cache.append({
                    "Fonte": os.path.basename(caminho),
                    "Data": item.get('data', 'N/A'),
                    "Reunião": item.get('nome_reuniao', 'N/A'),
                    "Linhas": linhas_extraidas
                })
            else:
                print(f"   ⚠️ PDF não encontrado ou arquivo vazio: {caminho}")

    # Salva o arquivo de cache JSON
    with open(CAMINHO_CACHE, 'w', encoding='utf-8') as f:
        json.dump(corpus_cache, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Cache construído com sucesso! {len(corpus_cache)} documentos processados e salvos.")
    return corpus_cache


def main():
    print("\n=== 🔍 MINI GOOGLE: CMTT ===")
    print("1. Fazer busca rápida (usa o Cache)")
    print("2. Atualizar Cache (rode isso se adicionou PDFs novos)")
    escolha = input("Escolha (1 ou 2): ")

    if escolha == '2':
        corpus = construir_ou_carregar_cache(forcar_atualizacao=True)
    else:
        corpus = construir_ou_carregar_cache()

    # Trava de segurança para não fechar em silêncio
    if not corpus:
        print("❌ O cache está vazio. Rode a Opção 2 para tentar extrair os PDFs novamente.")
        return

    print(f"\n📚 Base de dados pronta! {len(corpus)} atas carregadas na memória.")

    termo = input("\n⌨️ Digite o termo de busca (flexível): ")
    regex = criar_padrao_flexivel(termo)
    if not regex: return

    resultados = []

    # Busca instantânea
    for documento in corpus:
        for linha in documento["Linhas"]:
            if regex.search(linha):
                resultados.append({
                    "Data": documento['Data'],
                    "Reunião/Origem": documento['Reunião'],
                    "Contexto": linha.strip(),
                    "Fonte": documento['Fonte']
                })

    # Relatório Final
    if resultados:
        df = pd.DataFrame(resultados)
        print("\n" + "=" * 80)
        print(df[['Data', 'Fonte', 'Contexto']].to_string(index=False))
        print("=" * 80)
        df.to_excel("ultimo_resultado_busca.xlsx", index=False)
        print(f"✅ {len(df)} ocorrências salvas em 'ultimo_resultado_busca.xlsx'")
    else:
        print("\n∅ Nada encontrado para este termo.")


if __name__ == "__main__":
    main()