import pandas as pd
import os
import numpy as np

# IMPORTA O MESMO BASE_DIR DO MOTOR (Fonte Única da Verdade!)
from extratores.gerenciador_io import BASE_DIR

# Agora os caminhos ficam iguaizinhos aos do motor de extração:
CAMINHO_CSV = os.path.join(BASE_DIR, "dados", "processados", "presenca_oficial.csv")
CAMINHO_RELATORIOS = os.path.join(BASE_DIR, "relatorios")

if not os.path.exists(CAMINHO_RELATORIOS):
    os.makedirs(CAMINHO_RELATORIOS)

def gerar_relatorio_cadeiras():
    print(f"📊 Lendo dados oficiais de: {CAMINHO_CSV}")

    if not os.path.exists(CAMINHO_CSV):
        print("❌ Arquivo não encontrado! Rode o 'motor_extracao.py' primeiro.")
        return

    # Lê o CSV garantindo a codificação correta
    df = pd.read_csv(CAMINHO_CSV, sep=';', encoding='utf-8-sig')

    # BLINDAGEM: Garante que o Pandas lê a data corretamente
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df = df.dropna(subset=['Data'])

    print("⏳ Gerando Matriz Histórica Consolidada...")
    # Agrupa pegando o valor MÁXIMO de presença (Se titular ou suplente foi, a cadeira ganha 1)
    df_cadeira = df.groupby(['Data', 'Reuniao', 'Segmento', 'Cadeira'])['Presente'].max().reset_index()

    datas_unicas = sorted(df_cadeira['Data'].unique())
    colunas_ordenadas = []
    mapa_datas = {}

    for dt in datas_unicas:
        nome_reuniao = df_cadeira[df_cadeira['Data'] == dt]['Reuniao'].iloc[0]
        dt_str = dt.strftime('%d/%m/%Y')
        nome_coluna = f"{dt_str} - {nome_reuniao}"
        mapa_datas[dt] = nome_coluna
        colunas_ordenadas.append(nome_coluna)

    df_cadeira['Header_Reuniao'] = df_cadeira['Data'].map(mapa_datas)

    matriz = df_cadeira.pivot_table(
        index=['Segmento', 'Cadeira'],
        columns='Header_Reuniao',
        values='Presente',
        aggfunc='max'
    )

    matriz = matriz.reindex(columns=colunas_ordenadas)
    matriz['Reunioes_Existentes'] = matriz[colunas_ordenadas].count(axis=1)
    matriz['Total_Presencas'] = matriz[colunas_ordenadas].sum(axis=1)

    matriz['Taxa_Absenteismo_%'] = np.where(
        matriz['Reunioes_Existentes'] > 0,
        ((1 - (matriz['Total_Presencas'] / matriz['Reunioes_Existentes'])) * 100).round(1),
        0
    )

    matriz_final = matriz.reset_index()
    matriz_final.sort_values(by=['Segmento', 'Taxa_Absenteismo_%'], ascending=[True, False], inplace=True)

    print("⏳ Gerando Ranking de Rotatividade...")
    rotatividade = df.groupby(['Segmento', 'Cadeira'])['Nome'].nunique().reset_index()
    rotatividade.columns = ['Segmento', 'Cadeira Padronizada', 'Qtd_Nomes_Diferentes_Historico']
    rotatividade.sort_values(by='Qtd_Nomes_Diferentes_Historico', ascending=False, inplace=True)

    arquivo_saida = os.path.join(CAMINHO_RELATORIOS, "Relatorio_Cadeiras_Absenteismo.xlsx")

    with pd.ExcelWriter(arquivo_saida) as writer:
        matriz_final.to_excel(writer, sheet_name="Matriz e Absenteismo", index=False)
        rotatividade.to_excel(writer, sheet_name="Rotatividade de Nomes", index=False)

    print(f"✅ RELATÓRIO DE CADEIRAS PRONTO! Salvo em: {arquivo_saida}")

if __name__ == "__main__":
    gerar_relatorio_cadeiras()