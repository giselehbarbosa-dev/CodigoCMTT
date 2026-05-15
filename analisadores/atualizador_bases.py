"""
Módulo: Atualizador de Bases (Human-in-the-Loop)
Objetivo: Lê o gabarito preenchido pela auditoria humana na pasta de processados,
corrige as presenças na base oficial e gera a Camada Prata.
"""

import os
import pandas as pd
from core import config_ambiente

def atualizar_bases_com_auditoria():
    print("==========================================================")
    print("🔄 INICIANDO A CONSOLIDAÇÃO DA CAMADA PRATA (V1.1)")
    print("==========================================================\n")

    # 🎯 Mudamos a leitura para a pasta PROCESSADOS
    caminho_auditoria = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "Auditoria_Humana_XAI.xlsx")
    caminho_presenca = config_ambiente.CAMINHO_CSV_PRESENCA
    caminho_visitantes = config_ambiente.CAMINHO_CSV_VISITANTES

    if not os.path.exists(caminho_auditoria):
        print(f"❌ ERRO: Arquivo de Auditoria não encontrado em {caminho_auditoria}.")
        print("Certifique-se de que rodou o relatorio_cadeiras e preencheu o Excel.")
        return

    print("⏳ Lendo as bases brutas (Bronze) e o Gabarito da Auditoria...")
    df_pres = pd.read_csv(caminho_presenca, sep=';')
    df_vis = pd.read_csv(caminho_visitantes, sep=';')
    df_auditoria = pd.read_excel(caminho_auditoria, sheet_name='Tarefas_Auditoria')

    df_pres['Data'] = df_pres['Data'].astype(str).str.strip()
    df_vis['Data'] = df_vis['Data'].astype(str).str.strip()

    coluna_humana = [col for col in df_auditoria.columns if 'Conferencia_Humana' in col]
    if not coluna_humana:
        print("❌ ERRO: Coluna 'Conferencia_Humana' não encontrada no arquivo Excel.")
        return
    coluna_humana = coluna_humana[0]

    df_preenchido = df_auditoria[df_auditoria[coluna_humana].notna() & (df_auditoria[coluna_humana].str.strip() != '')]

    if df_preenchido.empty:
        print("⚠️ Nenhuma conferência preenchida encontrada no Excel. As bases não serão alteradas.")
        return

    print(f"✅ Encontradas {len(df_preenchido)} respostas da auditoria. Processando...\n")

    col_assoc_vis = 'Nome_Oficial_Associado' if 'Nome_Oficial_Associado' in df_vis.columns else 'Nome_Associado'
    alteracoes_presente = 0
    alteracoes_visitante = 0
    alteracoes_descarte = 0

    for _, row in df_preenchido.iterrows():
        resposta = str(row[coluna_humana]).strip().upper()
        ref_reuniao = str(row['Reuniao_Referencia'])
        data_ata = ref_reuniao.split(' - ')[-1].strip()
        nome = str(row['Nome_do_Conselheiro']).strip()
        segmento = str(row['Segmento']).strip()
        cadeira = str(row['Cadeira_Original']).strip()

        if resposta == 'P':
            mascara_pres = (df_pres['Data'] == data_ata) & (df_pres['Nome'].str.strip() == nome) & \
                           (df_pres['Segmento'].str.strip() == segmento) & (df_pres['Cadeira'].str.strip() == cadeira)

            if df_pres.loc[mascara_pres, 'Presente'].sum() == 0:
                df_pres.loc[mascara_pres, 'Presente'] = 1
                alteracoes_presente += 1

            mascara_vis = (df_vis['Data'] == data_ata) & (df_vis[col_assoc_vis].str.strip() == nome)
            df_vis = df_vis[~mascara_vis]

        elif resposta == 'V':
            alteracoes_visitante += 1

        elif resposta == '-':
            mascara_vis = (df_vis['Data'] == data_ata) & (df_vis[col_assoc_vis].str.strip() == nome)
            df_vis = df_vis[~mascara_vis]
            alteracoes_descarte += 1

    caminho_pres_conferido = caminho_presenca.replace('.csv', '_conferido.csv')
    caminho_vis_conferido = caminho_visitantes.replace('.csv', '_conferido.csv')

    df_pres.to_csv(caminho_pres_conferido, sep=';', index=False, encoding='utf-8-sig')
    df_vis.to_csv(caminho_vis_conferido, sep=';', index=False, encoding='utf-8-sig')

    print("==========================================================")
    print("📊 RELATÓRIO DA AUDITORIA APLICADA:")
    print(f" 🟩 Faltas corrigidas para PRESENÇA: {alteracoes_presente}")
    print(f" 🟦 Suspeitas confirmadas como VISITANTE: {alteracoes_visitante}")
    print(f" 🗑️ Fragmentos apagados (DESCARTE): {alteracoes_descarte}")
    print("==========================================================")
    print(f"💾 Base Prata salva com sucesso!")

if __name__ == "__main__":
    atualizar_bases_com_auditoria()