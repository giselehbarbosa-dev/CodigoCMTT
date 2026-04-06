import sys
import os
import re
import json
import pandas as pd

# 1. Ajuste do Path para encontrar a pasta core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente
from core.gerenciador_io import ler_texto_pdf, carregar_index_atas

# 🆕 A ÚNICA MUDANÇA: Importamos o construtor centralizado
from construtores.construtor_cache import construir_cache_novo

# 2. Define onde o cache oculto será salvo usando o nosso mapa
CAMINHO_CACHE = config_ambiente.CAMINHO_CACHE_BUSCADOR


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

    # 🆕 Se precisar construir, chama a função do nosso construtor!
    construir_cache_novo()

    # Após a construção, carrega e retorna
    with open(CAMINHO_CACHE, 'r', encoding='utf-8') as f:
        return json.load(f)


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

            # Amarração: Salvando e imprimindo usando as variáveis do config_ambiente!
            df.to_excel(config_ambiente.CAMINHO_EXCEL_BUSCA, index=False)
            print(f"✅ {len(df)} ocorrências salvas em '{config_ambiente.NOME_EXCEL_BUSCA}'")
        else:
            print("\n∅ Nada encontrado para este termo.")


if __name__ == "__main__":
    main()