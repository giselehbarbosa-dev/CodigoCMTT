import pandas as pd
import os

# IMPORTA O MESMO BASE_DIR DO MOTOR
from extratores.gerenciador_io import BASE_DIR

CAMINHO_GERAL = os.path.join(BASE_DIR, "dados", "processados", "visitantes_geral.csv")
CAMINHO_RELATORIOS = os.path.join(BASE_DIR, "relatorios")

if not os.path.exists(CAMINHO_RELATORIOS):
    os.makedirs(CAMINHO_RELATORIOS)

def gerar_relatorio_visitantes():
    print(f"📊 Lendo dados unificados de visitantes de: {CAMINHO_GERAL}")

    if not os.path.exists(CAMINHO_GERAL):
        print("❌ Arquivo unificado não encontrado! Rode o 'motor_extracao.py' primeiro.")
        return

    # Lê o arquivo OBT (One Big Table)
    df_visitantes = pd.read_csv(CAMINHO_GERAL, sep=';', encoding='utf-8-sig')

    if df_visitantes.empty:
        print("⚠️ O arquivo de visitantes está vazio.")
        return

    df_visitantes['Data'] = pd.to_datetime(df_visitantes['Data'], errors='coerce').dt.strftime('%d/%m/%Y')

    # SEPARANDO OS PÚBLICOS USANDO A COLUNA 'Tipo_Visitante'
    mask_ex_conselheiros = df_visitantes['Tipo_Visitante'].str.contains('Ex-Conselheiro', na=False, case=False)
    df_ex = df_visitantes[mask_ex_conselheiros].copy()
    df_ext_comuns = df_visitantes[~mask_ex_conselheiros].copy()

    arquivo_saida = os.path.join(CAMINHO_RELATORIOS, "Relatorio_Visitantes_Lobby.xlsx")

    with pd.ExcelWriter(arquivo_saida) as writer:

        # 1. ABA DE TODOS OS VISITANTES (A Base Completa)
        df_visitantes.to_excel(writer, sheet_name="Todos_os_Visitantes", index=False)

        # 2. RANKING DE EX-CONSELHEIROS
        if not df_ex.empty:
            rank_ex = df_ex.groupby(
                # 👇 AQUI! Trocamos 'Segmento_Anterior' por 'Segmento'
                ['Nome_Oficial_Associado', 'Tipo_Visitante', 'Periodo_Mandato', 'Segmento']
            ).size().reset_index(name='Total_Presencas_Pos_Mandato')

            rank_ex = rank_ex.sort_values(by='Total_Presencas_Pos_Mandato', ascending=False)
            rank_ex.to_excel(writer, sheet_name="Ranking_Ex_Conselheiros", index=False)

        # 3. RANKING DE VISITANTES COMUNS (O Filtro do Lobby)
        if not df_ext_comuns.empty:
            df_ext_comuns['Nome_Oficial_Associado'] = df_ext_comuns['Nome_Oficial_Associado'].fillna("")

            rank_comum = df_ext_comuns.groupby(
                ['Nome_na_Ata', 'Tipo_Visitante', 'Nome_Oficial_Associado']
            ).size().reset_index(name='Total_Presencas')

            rank_comum = rank_comum.sort_values(by='Total_Presencas', ascending=False)

            # Limpa o ruído: mostra só quem foi mais de 1 vez
            rank_comum_limpo = rank_comum[rank_comum['Total_Presencas'] > 1]
            rank_comum_limpo.to_excel(writer, sheet_name="Ranking_Visitantes_Comuns", index=False)

    print(f"✅ RELATÓRIO DE VISITANTES PRONTO! Salvo em: {arquivo_saida}")


if __name__ == "__main__":
    gerar_relatorio_visitantes()