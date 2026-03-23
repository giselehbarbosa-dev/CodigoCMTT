"""
Módulo: Exportador de Bases para Dashboards em Excel
"""
import os
import pandas as pd
from core import config_ambiente

PASTA_DADOS = config_ambiente.CAMINHO_PROCESSADOS
PASTA_GRAFICOS = config_ambiente.CAMINHO_GRAFICOS

# Consome do GPS
CSV_PRESENCA = config_ambiente.CAMINHO_CSV_PRESENCA
CSV_VISITANTES = config_ambiente.CAMINHO_CSV_VISITANTES

# Exporta pelo GPS
EXCEL_SAIDA = config_ambiente.CAMINHO_EXCEL_GRAFICOS

os.makedirs(PASTA_GRAFICOS, exist_ok=True)

def mapear_macro_forcas(segmento):
    seg = str(segmento).upper()
    if 'SOCIEDADE CIVIL' in seg: return 'Sociedade Civil'
    elif 'OPERADORES' in seg or 'SETOR EMPRESARIAL' in seg: return 'Operadores'
    elif 'ÓRGÃO' in seg or 'PÚBLICO' in seg or 'MUNICIPAL' in seg: return 'Poder Público'
    return 'Outros'

# ==========================================
# 2. PROCESSAMENTO DAS TABELAS
# ==========================================
def gerar_tabelas_excel():
    print("==========================================================")
    print("📊 INICIANDO EXPORTAÇÃO PARA EXCEL (MOTOR HÍBRIDO)")
    print("==========================================================\n")

    if not os.path.exists(CSV_PRESENCA) or not os.path.exists(CSV_VISITANTES):
        print(f"❌ ERRO: As bases de dados não foram encontradas na pasta {PASTA_DADOS}.")
        return

    print("⏳ Lendo bases de dados oficiais...")
    df_pres = pd.read_csv(CSV_PRESENCA, sep=';')
    df_vis = pd.read_csv(CSV_VISITANTES, sep=';')

    df_pres['Macro_Forca'] = df_pres['Segmento'].apply(mapear_macro_forcas)

    # Inicia o gravador de Excel
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
            sup_resumo['% Homens'] = (sup_resumo['M'] / sup_resumo['Total']) * 100
            sup_resumo.to_excel(writer, sheet_name='2. Suplencia_Mandato', index=False)
        else:
            print("   ⚠️ AVISO: Coluna 'Periodo_Mandato' não encontrada. Pulando esta aba.")

        # --- TABELA 3: PARIDADE POR ANO/SEGMENTO ---
        print("📈 Preparando Tabela 3: Paridade Diacrônica (Ano a Ano)...")
        df_pres['Ano'] = pd.to_datetime(df_pres['Data'], errors='coerce').dt.year
        df_ano = df_pres.dropna(subset=['Ano'])
        df_ano_gen = df_ano[df_ano['Genero'].isin(['F', 'M'])]
        df_ano_unicos = df_ano_gen.drop_duplicates(subset=['Ano', 'Macro_Forca', 'Cadeira', 'Nome', 'Genero'])

        ano_resumo = df_ano_unicos.groupby(['Ano', 'Macro_Forca', 'Genero']).size().unstack(fill_value=0).reset_index()
        ano_resumo['Total'] = ano_resumo['F'] + ano_resumo['M']
        ano_resumo['% Mulheres'] = (ano_resumo['F'] / ano_resumo['Total']) * 100
        ano_resumo.to_excel(writer, sheet_name='3. Evolucao_Ano', index=False)

        # --- TABELA 4: ROTATIVIDADE VS ASSIDUIDADE ---
        print("📈 Preparando Tabela 4: Saúde Democrática das Cadeiras...")
        stats = df_pres.groupby('Cadeira').agg(
            Assiduidade_Perc=('Presente', lambda x: x.mean() * 100),
            Qtd_Pessoas_Diferentes=('Nome', 'nunique')
        ).reset_index()
        stats.to_excel(writer, sheet_name='4. Saude_Cadeiras', index=False)

        # --- TABELA 5: TEIA DE LOBBY (Visitantes Frequentes) ---
        print("📈 Preparando Tabela 5: Frequência de Ex-Conselheiros (Lobby)...")
        ex_cons = df_vis[df_vis['Tipo_Visitante'].str.contains('Ex-Conselheiro', na=False)]
        lobby = ex_cons['Nome_na_Ata'].value_counts().reset_index()
        lobby.columns = ['Ex_Conselheiro', 'Frequencia_como_Visitante']
        lobby.to_excel(writer, sheet_name='5. Lobby_Visitantes', index=False)

    print(f"\n🎉 SUCESSO! O seu arquivo Excel está pronto na pasta: {PASTA_GRAFICOS}")
    print("Abra o arquivo 'Base_Para_Graficos_CMTT.xlsx' para criar seus painéis.")

if __name__ == "__main__":
    gerar_tabelas_excel()