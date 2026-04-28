"""
Módulo: Exportador de Bases para Dashboards em Excel
Objetivo: Realizar o processamento matemático e unificação dinâmica de nomes (Entity Resolution)
utilizando o motor NLP oficial do projeto para gerar insumos para o Excel.
"""

import os
import pandas as pd
from thefuzz import fuzz
from utils.config_filtros import mapear_macro_forcas

# Importando a inteligência da SUA arquitetura!
from core import config_ambiente
from utils.config_filtros import normalizar

# ==========================================
# 1. CONFIGURAÇÕES E DIRETÓRIOS (GPS Dinâmico)
# ==========================================
PASTA_DADOS = config_ambiente.CAMINHO_PROCESSADOS
PASTA_GRAFICOS = config_ambiente.CAMINHO_GRAFICOS

CSV_PRESENCA = config_ambiente.CAMINHO_CSV_PRESENCA
CSV_VISITANTES = config_ambiente.CAMINHO_CSV_VISITANTES
EXCEL_SAIDA = config_ambiente.CAMINHO_EXCEL_GRAFICOS

os.makedirs(PASTA_GRAFICOS, exist_ok=True)

# ==========================================
# 2. MOTOR DE PROCESSAMENTO
# ==========================================
def gerar_tabelas_excel():
    print("==========================================================")
    print("📊 INICIANDO EXPORTAÇÃO PARA EXCEL (MOTOR ESCALÁVEL)")
    print("==========================================================\n")

    if not os.path.exists(CSV_PRESENCA) or not os.path.exists(CSV_VISITANTES):
        print(f"❌ ERRO: Bases de dados não encontradas em {PASTA_DADOS}.")
        return

    print("⏳ Lendo bases de dados processadas na Fase 1...")
    df_pres = pd.read_csv(CSV_PRESENCA, sep=';')
    df_vis = pd.read_csv(CSV_VISITANTES, sep=';')

    df_pres['Macro_Forca'] = df_pres['Segmento'].apply(mapear_macro_forcas)

    with pd.ExcelWriter(EXCEL_SAIDA, engine='openpyxl') as writer:

        # --- TABELA 1: COMPOSIÇÃO DE FORÇAS ---
        print("📈 Preparando Tabela 1: Composição de Forças...")
        df_cadeiras = df_pres.dropna(subset=['Macro_Forca', 'Segmento', 'Cadeira'])
        comp = df_cadeiras[['Macro_Forca', 'Segmento', 'Cadeira']].drop_duplicates()
        comp_resumo = comp.groupby(['Macro_Forca', 'Segmento']).size().reset_index(name='Qtd_Cadeiras')
        comp_resumo.to_excel(writer, sheet_name='1. Composicao', index=False)

        # --- TABELA 2: GARGALO DA SUPLÊNCIA POR MANDATO ---
        print("📈 Preparando Tabela 2: Suplência por Mandato...")
        if 'Periodo_Mandato' in df_pres.columns:
            df_sup = df_pres[df_pres['Tipo'].str.upper().str.strip().isin(['TITULAR', 'SUPLENTE']) & df_pres['Genero'].isin(['F', 'M'])]
            df_sup_unicos = df_sup.drop_duplicates(subset=['Periodo_Mandato', 'Cadeira', 'Nome', 'Tipo', 'Genero'])

            sup_resumo = df_sup_unicos.groupby(['Periodo_Mandato', 'Tipo', 'Genero']).size().unstack(fill_value=0).reset_index()
            sup_resumo['Total'] = sup_resumo['F'] + sup_resumo['M']
            sup_resumo['% Mulheres'] = (sup_resumo['F'] / sup_resumo['Total']) * 100
            sup_resumo.to_excel(writer, sheet_name='2. Suplencia_Mandato', index=False)

        # --- TABELA 3: PARIDADE POR ANO (EVOLUÇÃO) ---
        print("📈 Preparando Tabela 3: Evolução da Paridade...")
        df_pres['Ano'] = pd.to_datetime(df_pres['Data'], errors='coerce').dt.year
        df_ano_gen = df_pres[df_pres['Genero'].isin(['F', 'M'])].dropna(subset=['Ano'])
        df_ano_unicos = df_ano_gen.drop_duplicates(subset=['Ano', 'Macro_Forca', 'Cadeira', 'Nome', 'Genero'])

        ano_resumo = df_ano_unicos.groupby(['Ano', 'Macro_Forca', 'Genero']).size().unstack(fill_value=0).reset_index()
        ano_resumo['Total'] = ano_resumo['F'] + ano_resumo['M']
        ano_resumo['% Mulheres'] = (ano_resumo['F'] / ano_resumo['Total']) * 100
        ano_resumo.to_excel(writer, sheet_name='3. Evolucao_Ano', index=False)

        # --- TABELA 4: SAÚDE DAS CADEIRAS ---
        print("📈 Preparando Tabela 4: Rotatividade e Assiduidade...")
        stats = df_pres.groupby('Cadeira').agg(
            Assiduidade_Perc=('Presente', lambda x: x.mean() * 100),
            Qtd_Pessoas_Diferentes=('Nome', 'nunique')
        ).reset_index()
        stats.to_excel(writer, sheet_name='4. Saude_Cadeiras', index=False)

        # --- TABELA 5: TEIA DE LOBBY (USANDO O SEU MOTOR NLP) ---
        print("📈 Preparando Tabela 5: Teia de Lobby (IA de Nomes)...")
        ex_cons = df_vis[df_vis['Tipo_Visitante'].str.contains('Ex-Conselheiro', na=False)].copy()

        print("   🔍 Executando IA de Unificação Dinâmica de Nomes (via config_filtros)...")
        nomes_unicos = ex_cons['Nome_na_Ata'].dropna().str.strip().unique()
        nomes_unicos = sorted(nomes_unicos, key=len, reverse=True)

        dicionario_dinamico = {}

        for nome_curto in nomes_unicos:
            matches = []
            # Usando a sua função oficial 'normalizar' do projeto!
            nome_curto_limpo = normalizar(nome_curto)

            for nome_longo in nomes_unicos:
                if len(nome_longo) <= len(nome_curto) or nome_longo == nome_curto:
                    continue

                nome_longo_limpo = normalizar(nome_longo)

                if fuzz.token_set_ratio(nome_curto_limpo, nome_longo_limpo) > 95:
                    matches.append(nome_longo)

            if len(matches) == 1:
                dicionario_dinamico[nome_curto] = matches[0]

        ex_cons['Nome_na_Ata'] = ex_cons['Nome_na_Ata'].str.strip().replace(dicionario_dinamico)
        lobby = ex_cons['Nome_na_Ata'].value_counts().reset_index()
        lobby.columns = ['Ex_Conselheiro', 'Frequencia_como_Visitante']
        lobby.to_excel(writer, sheet_name='5. Lobby_Visitantes', index=False)

    print(f"\n🎉 SUCESSO! Arquivo gerado em: {EXCEL_SAIDA}")

if __name__ == "__main__":
    gerar_tabelas_excel()