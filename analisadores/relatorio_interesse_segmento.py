"""
Módulo: Relatório de Interesse por Segmento (Camada Ouro)
Objetivo: Cruza a base de presenças AUDITADA com a base temática.
Relacionamento: Realizado através da chave primária 'Arquivo'.
"""

import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import config_ambiente


def gerar_indice_interesse():
    print("==========================================================")
    print("🧠 CALCULANDO ÍNDICE DE INTERESSE (PAUTA VS PRESENÇA AUDITADA)")
    print("==========================================================")

    # 1. DEFINIÇÃO DE CAMINHOS (Ponto Crítico: Usar a base auditada)
    # Puxamos o caminho base original do config e adicionamos o sufixo correto da Camada Prata
    caminho_presenca = config_ambiente.CAMINHO_CSV_PRESENCA.replace('.csv', '_conferido.csv')

    caminho_temas = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "temas_debatidos.csv")

    if not os.path.exists(caminho_presenca):
        print(f"❌ Base Prata não encontrada em: {caminho_presenca}")
        print("💡 Rode o 'atualizador_bases.py' primeiro para consolidar a auditoria da Isa.")
        return

    if not os.path.exists(caminho_temas):
        print(f"❌ Base temática não encontrada em: {caminho_temas}")
        return
    
    # 2. CARREGAMENTO DOS DADOS
    df_presenca = pd.read_csv(caminho_presenca, sep=';', encoding='utf-8-sig')
    df_temas = pd.read_csv(caminho_temas, sep=';', encoding='utf-8-sig')

    # 3. FILTRAGEM TEMÁTICA (Sarrafo de Fidelidade da Tese: >= 12%)
    # Consideramos apenas pautas que de fato estruturaram a reunião
    df_temas_focados = df_temas[df_temas['Relevancia_(%)'] >= 12.0].copy()

    # 4. CÁLCULO DE QUÓRUM POR SEGMENTO
    # Agrupamos por Arquivo (Chave Primária) e Segmento para ver quem apareceu
    # A base auditada mantém o padrão 0/1 na coluna 'Presente'
    quorum_reuniao = df_presenca.groupby(['Arquivo', 'Segmento']).agg(
        Cadeiras_Totais=('Presente', 'count'),
        Cadeiras_Ocupadas=('Presente', 'sum')
    ).reset_index()

    quorum_reuniao['Taxa_Comparecimento_(%)'] = (
            (quorum_reuniao['Cadeiras_Ocupadas'] / quorum_reuniao['Cadeiras_Totais']) * 100
    ).round(1)

    # 5. O CRUZAMENTO RELACIONAL (JOIN)
    # Unimos a pauta dominante ao quórum de presença através do nome do arquivo (PDF)
    cruzamento = pd.merge(df_temas_focados, quorum_reuniao, on='Arquivo', how='inner')

    # 6. AGREGAÇÃO PARA O BI (Interesse Histórico)
    indice_interesse = cruzamento.groupby(['Tema_Classificado', 'Segmento']).agg(
        Vezes_Pautado_Com_Foco=('Arquivo', 'nunique'),
        Media_Comparecimento_Historica=('Taxa_Comparecimento_(%)', 'mean')
    ).reset_index()

    indice_interesse['Media_Comparecimento_Historica'] = indice_interesse['Media_Comparecimento_Historica'].round(1)

    # Ordena para facilitar a leitura no BI
    indice_interesse = indice_interesse.sort_values(
        by=['Tema_Classificado', 'Media_Comparecimento_Historica'],
        ascending=[True, False]
    )

    # 7. EXPORTAÇÃO DO DATA MART
    dir_saida = os.path.join(config_ambiente.BASE_DIR, "outputs", "relatorios")
    caminho_saida = os.path.join(dir_saida, "bi_indice_interesse_segmento.csv")

    indice_interesse.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')

    print(f"✅ Sucesso! O índice de interesse foi gerado com base nos dados auditados.")
    print(f"📊 Foram processadas {len(df_temas_focados)} pautas dominantes.")


if __name__ == "__main__":
    gerar_indice_interesse()