import pandas as pd
import os

BASE_DIR = r"/"
CAMINHO_HISTORICO = os.path.join(BASE_DIR, "analisadores/dados", "processados", "visitantes_historico.csv")
CAMINHO_EXTERNOS = os.path.join(BASE_DIR, "analisadores/dados", "processados", "visitantes_externos.csv")
CAMINHO_RELATORIOS = os.path.join(BASE_DIR, "../relatorios")

if not os.path.exists(CAMINHO_RELATORIOS): os.makedirs(CAMINHO_RELATORIOS)


def ler_arquivo(caminho):
    if not os.path.exists(caminho): return pd.DataFrame()
    return pd.read_csv(caminho, sep=';')


def gerar_relatorio_visitantes():
    print("📊 Gerando Relatórios de Visitantes...")

    df_hist = ler_arquivo(CAMINHO_HISTORICO)
    df_ext = ler_arquivo(CAMINHO_EXTERNOS)

    arquivo_saida = os.path.join(CAMINHO_RELATORIOS, "Relatorio_Visitantes_Lobby.xlsx")

    with pd.ExcelWriter(arquivo_saida) as writer:

        if not df_hist.empty:
            df_hist['Data'] = pd.to_datetime(df_hist['Data'], errors='coerce').dt.strftime('%d/%m/%Y')
            rank_hist = df_hist['Nome_Original'].value_counts().reset_index()
            rank_hist.columns = ['Ex-Conselheiro', 'Frequência Pós-Mandato']

            df_hist.to_excel(writer, sheet_name="Histórico_Detalhado", index=False)
            rank_hist.to_excel(writer, sheet_name="Ranking_Historico", index=False)

        if not df_ext.empty:
            df_ext['Data'] = pd.to_datetime(df_ext['Data'], errors='coerce').dt.strftime('%d/%m/%Y')

            # PREPARAÇÃO PARA O NOVO AGRUPAMENTO
            # Preenche os "NaN" com espaço vazio para o groupby não apagar os visitantes comuns
            if 'Nome_Associado' in df_ext.columns:
                df_ext['Nome_Associado'] = df_ext['Nome_Associado'].fillna("")
                rank_ext = df_ext.groupby(['Nome', 'Tipo', 'Nome_Associado']).size().reset_index(name='Total Presenças')
            else:
                # Fallback caso a coluna ainda não exista
                rank_ext = df_ext.groupby(['Nome', 'Tipo']).size().reset_index(name='Total Presenças')

            # Ordena do maior para o menor número de presenças
            rank_ext = rank_ext.sort_values(by='Total Presenças', ascending=False)

            # Pessoas que foram mais de 1 vez (Filtra o lixo ocasional)
            rank_ext_limpo = rank_ext[rank_ext['Total Presenças'] > 1]

            df_ext.to_excel(writer, sheet_name="Externos_Detalhado", index=False)
            rank_ext_limpo.to_excel(writer, sheet_name="Ranking_Externos_Lobby", index=False)

    print(f"✅ RELATÓRIO DE VISITANTES PRONTO! Salvo em: {arquivo_saida}")


if __name__ == "__main__":
    gerar_relatorio_visitantes()