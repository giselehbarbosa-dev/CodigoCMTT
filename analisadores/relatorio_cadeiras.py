"""
Módulo: Relatório de Cadeiras (Explainable AI / Auditoria Visual)
Objetivo: Gerar DOIS arquivos de saída:
1. Relatório de Cadeiras Absenteismo (Snapshot histórico -> Vai para Outputs/Relatorios).
2. Auditoria Humana XAI (Lista incremental -> Vai para Dados/Processados).
"""

import os
import re
import pandas as pd
from openpyxl.styles import PatternFill, Font, Alignment
from core import config_ambiente

def gerar_relatorio_cadeiras():
    print("==========================================================")
    print("📊 INICIANDO GERAÇÃO DOS ARQUIVOS DE AUDITORIA (XAI - V6.6)")
    print("==========================================================\n")

    if not os.path.exists(config_ambiente.CAMINHO_CSV_PRESENCA) or not os.path.exists(config_ambiente.CAMINHO_CSV_VISITANTES):
        print("❌ ERRO: Bases de dados não encontradas.")
        return

    print("⏳ Lendo bases e processando metadados...")
    df_pres = pd.read_csv(config_ambiente.CAMINHO_CSV_PRESENCA, sep=';')
    df_vis = pd.read_csv(config_ambiente.CAMINHO_CSV_VISITANTES, sep=';')

    df_pres['Data'] = df_pres['Data'].astype(str).str.strip()
    df_vis['Data'] = df_vis['Data'].astype(str).str.strip()

    df_pres['Data_DT'] = pd.to_datetime(df_pres['Data'], format='%d/%m/%Y', errors='coerce')
    if df_pres['Data_DT'].isnull().all():
        df_pres['Data_DT'] = pd.to_datetime(df_pres['Data'], errors='coerce')

    regras = config_ambiente.REGRAS_CONSELHO
    termo_extra = regras.get("termo_reuniao_extra", "Extraordinária")
    regex_extra = regras.get("regex_arquivo_extra", r"extra_(\d+)")
    label_ia = regras.get("label_auditoria_ia", "Possível Conselheiro")

    if 'Reuniao' in df_pres.columns:
        def formatar_ata(x):
            match = re.search(r'(\d+)', str(x))
            if match: return f"{match.group(1).zfill(2)}ª"
            return pd.NA

        df_pres['Numero_Ata'] = df_pres['Reuniao'].apply(formatar_ata)

        if 'Arquivo' in df_pres.columns:
            masc_extra = df_pres['Reuniao'].astype(str).str.contains(termo_extra, case=False, na=False)
            num_extra = df_pres.loc[masc_extra, 'Arquivo'].astype(str).str.extract(regex_extra)[0]
            df_pres.loc[masc_extra, 'Numero_Ata'] = "Extra " + num_extra.str.zfill(2).fillna('?')

        df_pres['Numero_Ata'] = df_pres['Numero_Ata'].fillna('-')
        df_pres['Ref_Reuniao'] = df_pres['Numero_Ata'] + " - " + df_pres['Data']
    else:
        df_pres['Ref_Reuniao'] = df_pres['Data']

    col_assoc = 'Nome_Oficial_Associado' if 'Nome_Oficial_Associado' in df_vis.columns else 'Nome_Associado'

    print("🔍 Mapeando pendências e rastreando texto original...")
    filtro_pendentes = df_vis['Tipo_Visitante'].str.contains(label_ia, case=False, na=False)
    df_pendentes = df_vis[filtro_pendentes].dropna(subset=[col_assoc, 'Data'])

    dict_rastreio_ocr = {}
    for _, v_row in df_pendentes.iterrows():
        chave = (v_row[col_assoc].strip(), v_row['Data'].strip())
        dict_rastreio_ocr[chave] = v_row.get('Nome_na_Ata', 'Não capturado')

    tuplas_pendentes = set(dict_rastreio_ocr.keys())
    set_cadeira_pendente = set()
    lista_aba_auditoria = []

    for _, row in df_pres.iterrows():
        if row['Presente'] == 0:
            nome_indiv = str(row['Nome']).strip()
            data_bruta = str(row['Data']).strip()

            if (nome_indiv, data_bruta) in tuplas_pendentes:
                chave_info = (row['Segmento'], row['Cadeira'], row['Ref_Reuniao'])
                set_cadeira_pendente.add(chave_info)

                texto_original_ocr = dict_rastreio_ocr.get((nome_indiv, data_bruta), 'N/A')

                lista_aba_auditoria.append({
                    'Reuniao_Referencia': row['Ref_Reuniao'],
                    'Data_DT': row['Data_DT'],
                    'Segmento': row['Segmento'],
                    'Orgao_Representado': row.get('Orgao', 'N/A'),
                    'Cadeira_Original': row['Cadeira'],
                    'Nome_do_Conselheiro': nome_indiv,
                    'Nome_na_Ata (O que a IA leu)': texto_original_ocr,
                    'Tipo_Vinculo': str(row['Tipo']).strip(),
                    'Status_Sugerido': '⚠️ CONFERIR NO PDF',
                    'Conferencia_Humana (Digite: P=Presente, V=Visitante ou -=Descarte)': ''
                })

    print("📈 Consolidando matriz histórica...")
    df_cadeira_reuniao = df_pres.groupby(['Segmento', 'Cadeira', 'Ref_Reuniao', 'Data_DT'])['Presente'].max().reset_index()
    estat = df_cadeira_reuniao.groupby(['Segmento', 'Cadeira']).agg(Total=('Ref_Reuniao','count'), Pres=('Presente','sum')).reset_index()
    estat['Faltas'] = estat['Total'] - estat['Pres']
    estat['% Abs'] = (estat['Faltas'] / estat['Total'] * 100).round(1)

    matriz = df_cadeira_reuniao.pivot_table(index=['Segmento', 'Cadeira'], columns='Ref_Reuniao', values='Presente', aggfunc='max').fillna('N/A')
    cols_ord = df_cadeira_reuniao.sort_values('Data_DT')['Ref_Reuniao'].unique()
    matriz = matriz.reindex(columns=cols_ord).replace({1: 'Presente', 0: 'Falta'})

    for idx in matriz.index:
        for c in matriz.columns:
            if matriz.at[idx, c] == 'Falta' and (idx[0], idx[1], c) in set_cadeira_pendente:
                matriz.at[idx, c] = '⚠️ PENDENTE'

    matriz_final = pd.merge(estat, matriz.reset_index(), on=['Segmento', 'Cadeira'], how='left')

    # ========================================================
    # 🎯 LÓGICA INCREMENTAL DA AUDITORIA (NOVIDADE V6.6)
    # ========================================================
    print("🧩 Gerenciando Memória Acumulada do Gabarito...")
    path_auditoria = os.path.join(config_ambiente.CAMINHO_PROCESSADOS, "Auditoria_Humana_XAI.xlsx")

    # Prepara os dados novos
    df_novas_tarefas = pd.DataFrame(lista_aba_auditoria)
    if not df_novas_tarefas.empty:
        df_novas_tarefas = df_novas_tarefas.sort_values(by=['Data_DT', 'Segmento', 'Cadeira_Original']).drop(columns=['Data_DT'])

    # Verifica se já existe um arquivo antigo preenchido pela Isa
    if os.path.exists(path_auditoria):
        try:
            df_antigo = pd.read_excel(path_auditoria, sheet_name='Tarefas_Auditoria')

            if not df_novas_tarefas.empty:
                # Concatena o antigo com o novo
                df_consolidado = pd.concat([df_antigo, df_novas_tarefas], ignore_index=True)

                # Remove duplicatas mantendo o 'first' (que é a linha antiga onde a Isa já digitou algo)
                df_lista_auditoria = df_consolidado.drop_duplicates(
                    subset=['Reuniao_Referencia', 'Cadeira_Original', 'Nome_do_Conselheiro'],
                    keep='first'
                )
            else:
                df_lista_auditoria = df_antigo
        except Exception as e:
            print(f"⚠️ Erro ao ler planilha antiga de auditoria: {e}")
            df_lista_auditoria = df_novas_tarefas
    else:
        df_lista_auditoria = df_novas_tarefas

    # ========================================================
    # 🎯 EXPORTAÇÃO E FORMATAÇÃO
    # ========================================================
    path_matriz = config_ambiente.CAMINHO_EXCEL_CADEIRAS # outputs/relatorios
    os.makedirs(os.path.dirname(path_matriz), exist_ok=True)
    os.makedirs(os.path.dirname(path_auditoria), exist_ok=True)

    f_pnd = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    f_pre = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    f_fal = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    f_inp = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    font_pnd = Font(color="9C6500", bold=True)

    with pd.ExcelWriter(path_matriz, engine='openpyxl') as writer:
        matriz_final.to_excel(writer, sheet_name='Matriz_Snapshot_IA', index=False)
        ws1 = writer.sheets['Matriz_Snapshot_IA']
        ws1.freeze_panes = "G2"

        for row in ws1.iter_rows(min_row=2, min_col=7):
            for cell in row:
                val = str(cell.value)
                if 'Presente' in val: cell.fill = f_pre
                elif 'Falta' in val: cell.fill = f_fal
                elif '⚠️' in val: cell.fill = f_pnd; cell.font = font_pnd
                cell.alignment = Alignment(horizontal="center", vertical="center")

    if not df_lista_auditoria.empty:
        with pd.ExcelWriter(path_auditoria, engine='openpyxl') as writer:
            df_lista_auditoria.to_excel(writer, sheet_name='Tarefas_Auditoria', index=False)
            ws2 = writer.sheets['Tarefas_Auditoria']
            idx_inp = len(df_lista_auditoria.columns)

            for row in ws2.iter_rows(min_row=1):
                for cell in row:
                    if cell.column == idx_inp:
                        cell.fill = f_inp
                        if cell.row == 1: cell.font = Font(bold=True, color="9C6500")
                    elif '⚠️' in str(cell.value): cell.fill = f_pnd; cell.font = font_pnd
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    print(f"✅ Matriz (Ouro) salva em: {path_matriz}")
    print(f"✅ Auditoria (Prata/Staging) salva e atualizada em: {path_auditoria}")

if __name__ == "__main__":
    gerar_relatorio_cadeiras()