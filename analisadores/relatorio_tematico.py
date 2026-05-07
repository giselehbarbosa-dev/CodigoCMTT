"""
Módulo: Relatório Temático (Visões de BI)
Objetivo: Gerar tabelas pré-agregadas para o Power BI (Evolução, Palavras-chave).
Escalabilidade: 100% dinâmico através do config_ambiente (White-Label).
"""

import os
import sys
import pandas as pd

# Garante que o Python encontre a pasta raiz para importar o core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente

def formatar_palavra_nuvem(palavra_bruta):
    """Trata a raiz da palavra consumindo o dicionário visual do config_ambiente."""
    palavra = palavra_bruta.lower().strip()

    # Puxa dinamicamente as regras visuais da Fonte Única da Verdade
    if hasattr(config_ambiente, 'MAPA_PALAVRAS_BONITAS') and palavra in config_ambiente.MAPA_PALAVRAS_BONITAS:
        return config_ambiente.MAPA_PALAVRAS_BONITAS[palavra]

    # Fallback genérico para palavras que não estão no dicionário
    return palavra.title()

def gerar_visoes_tematicas():
    print("==========================================================")
    print("📊 GERANDO DATA MARTS TEMÁTICOS PARA O POWER BI")
    print("==========================================================")

    # Caminho do produto do motor_tematico
    caminho_temas = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv")

    if not os.path.exists(caminho_temas):
        print(f"❌ Arquivo não encontrado: {caminho_temas}")
        print("💡 Rode o motor_tematico.py primeiro.")
        return

    df_temas = pd.read_csv(caminho_temas, sep=';', encoding='utf-8-sig')

    # Define pasta de saída para os relatórios de BI
    dir_saida = os.path.join(config_ambiente.BASE_DIR, "outputs", "relatorios")
    os.makedirs(dir_saida, exist_ok=True)

    # ---------------------------------------------------------
    # VISÃO 1: EVOLUÇÃO TEMPORAL (Com Total de Reuniões e %)
    # ---------------------------------------------------------
    df_temas['Ano'] = df_temas['Data (AAAA/MM)'].astype(str).str[:4]

    # Conta o total de atas processadas naquele ano (denominador)
    total_reunioes_ano = df_temas.groupby('Ano')['Arquivo'].nunique().reset_index(name='Total_Reunioes_Ano')

    # Agrega a pontuação de relevância do tema
    visao_evolucao = df_temas.groupby(['Ano', 'Tema_Classificado']).agg(
        Ocorrencias_Totais=('Ocorrencias', 'sum'),
        Relevancia_Media_Anual=('Relevancia_(%)', 'mean'),
        Qtd_Reunioes_Apareceu=('Arquivo', 'count')
    ).reset_index()

    # Cruza com os totais anuais e calcula a taxa de presença
    visao_evolucao = pd.merge(visao_evolucao, total_reunioes_ano, on='Ano', how='left')
    visao_evolucao['%_Presenca_nas_Reunioes'] = ((visao_evolucao['Qtd_Reunioes_Apareceu'] / visao_evolucao['Total_Reunioes_Ano']) * 100).round(1)
    visao_evolucao['Relevancia_Media_Anual'] = visao_evolucao['Relevancia_Media_Anual'].round(1)

    # Reordena as colunas para o BI
    colunas_ordem = [
        'Ano', 'Tema_Classificado', 'Ocorrencias_Totais',
        'Relevancia_Media_Anual', 'Qtd_Reunioes_Apareceu',
        'Total_Reunioes_Ano', '%_Presenca_nas_Reunioes'
    ]
    visao_evolucao = visao_evolucao[colunas_ordem]

    caminho_evolucao = os.path.join(dir_saida, "bi_temas_evolucao_anual.csv")
    visao_evolucao.to_csv(caminho_evolucao, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ Visão 1: Evolução Anual salva em {caminho_evolucao}")

    # ---------------------------------------------------------
    # VISÃO 2: FREQUÊNCIA DE GATILHOS (Nuvem de Palavras)
    # ---------------------------------------------------------
    lista_palavras = []
    for _, row in df_temas.iterrows():
        if pd.notna(row.get('Palavras_Chave_Ativadas')):
            # Extrai e limpa a lista de palavras salva pelo motor
            palavras = str(row['Palavras_Chave_Ativadas']).split(',')
            for p in palavras:
                # Aciona a função que consome o config_ambiente dinamicamente
                palavra_bonita = formatar_palavra_nuvem(p)
                lista_palavras.append({
                    "Tema": row['Tema_Classificado'],
                    "Palavra": palavra_bonita,
                    "Ano": row['Ano']
                })

    if lista_palavras:
        df_palavras = pd.DataFrame(lista_palavras)
        visao_palavras = df_palavras.groupby(['Tema', 'Palavra']).size().reset_index(name='Vezes_Ativada')
        visao_palavras = visao_palavras.sort_values(by=['Tema', 'Vezes_Ativada'], ascending=[True, False])

        caminho_nuvem = os.path.join(dir_saida, "bi_temas_nuvem_palavras.csv")
        visao_palavras.to_csv(caminho_nuvem, index=False, sep=';', encoding='utf-8-sig')
        print(f"✅ Visão 2: Nuvem de Palavras tratada salva em {caminho_nuvem}")

    print("\n🏁 Processamento de temas concluído e pronto para o BI!")

if __name__ == "__main__":
    gerar_visoes_tematicas()