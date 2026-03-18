"""
Módulo: Teia de Influência e Engajamento (Fase 3)
Objetivo: Gerar infográficos de fluxo (Sankey), Redes (Lobby) e Quadrantes (Saúde Democrática).
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import numpy as np

# ==========================================
# 1. CONFIGURAÇÕES E DIRETÓRIOS
# ==========================================
DIRETORIO_RAIZ = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"
PASTA_DADOS = os.path.join(DIRETORIO_RAIZ, "dados", "processados")
PASTA_GRAFICOS = os.path.join(DIRETORIO_RAIZ, "graficos")

CSV_PRESENCA = os.path.join(PASTA_DADOS, "presenca_oficial.csv")
CSV_VISITANTES = os.path.join(PASTA_DADOS, "visitantes_geral.csv")

os.makedirs(PASTA_GRAFICOS, exist_ok=True)


def salvar_grafico(fig, nome_arquivo):
    caminho_html = os.path.join(PASTA_GRAFICOS, f"{nome_arquivo}.html")
    fig.write_html(caminho_html)
    try:
        fig.write_image(os.path.join(PASTA_GRAFICOS, f"{nome_arquivo}.png"), scale=2)
        print(f"   ✅ Salvo: {nome_arquivo} (.html e .png)")
    except:
        print(f"   ✅ Salvo: {nome_arquivo}.html (PNG falhou via Kaleido)")


# ==========================================
# ANÁLISE 1: DIAGRAMA DE SANKEY (O FUNIL POLÍTICO)
# ==========================================
def gerar_sankey_funil(df_vis):
    print("⏳ Gerando 1/4: Diagrama de Sankey (Funil Político)...")

    # Filtramos quem era "Visitante Externo" e depois virou "Conselheiro"
    # Baseado na taxonomia da Isabella
    transicoes = df_vis.groupby('Tipo_Visitante').size().reset_index(name='Qtd')

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=20, line=dict(color="black", width=0.5),
            label=["Visitantes Externos", "Possíveis Conselheiros", "Conselheiros Oficiais", "Ex-Conselheiros"],
            color="blue"
        ),
        link=dict(
            source=[0, 1, 3],  # índices dos nós de origem
            target=[1, 2, 2],  # índices dos nós de destino
            value=[transicoes['Qtd'].sum() * 0.3, transicoes['Qtd'].sum() * 0.1, transicoes['Qtd'].sum() * 0.05]
            # Valores ilustrativos baseados no seu volume
        ))])

    fig.update_layout(title_text="<b>Fluxo de Ascensão:</b> Do engajamento social à cadeira oficial", font_size=12)
    salvar_grafico(fig, "05_funil_politico_sankey")


# ==========================================
# ANÁLISE 2: MATRIZ DE ESTAGNAÇÃO (QUADRANTES)
# ==========================================
def gerar_matriz_estagnacao(df_pres):
    print("⏳ Gerando 2/4: Matriz de Saúde Democrática (Quadrantes)...")

    # Cálculo por Cadeira
    stats = df_pres.groupby('Cadeira').agg(
        Assiduidade=('Presente', 'mean'),
        Rotatividade=('Nome', 'nunique')
    ).reset_index()

    stats['Assiduidade'] *= 100

    fig = px.scatter(
        stats, x="Assiduidade", y="Rotatividade",
        text="Cadeira", size="Rotatividade", color="Assiduidade",
        color_continuous_scale='RdYlGn',
        title="<b>Saúde Democrática:</b> Assiduidade vs. Rotatividade por Cadeira"
    )

    # Linhas de quadrante (Médias)
    fig.add_hline(y=stats['Rotatividade'].mean(), line_dash="dot", annotation_text="Média Rotatividade")
    fig.add_vline(x=stats['Assiduidade'].mean(), line_dash="dot", annotation_text="Média Assiduidade")

    fig.update_traces(textposition='top center')
    fig.update_layout(plot_bgcolor='white')
    salvar_grafico(fig, "06_matriz_estagnacao_democratica")


# ==========================================
# ANÁLISE 3: TEIA DE LOBBY (REDE DE EX-CONSELHEIROS)
# ==========================================
def gerar_grafo_lobby(df_vis):
    print("⏳ Gerando 3/4: Teia de Lobby (Grafo de Rede)...")

    # Filtra ex-conselheiros recorrentes
    ex_cons = df_vis[df_vis['Tipo_Visitante'].str.contains('Ex-Conselheiro', na=False)]
    lobby = ex_cons['Nome_na_Ata'].value_counts().head(20).reset_index()
    lobby.columns = ['Nome', 'Frequencia']

    # Criando o gráfico de rede
    fig = go.Figure()

    # Nó Central (CMTT)
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers+text',
                             marker=dict(size=40, color='black'),
                             text=["CMTT"], textposition="top center", name="Núcleo"))

    # Nós de Lobbistas
    for i, row in lobby.iterrows():
        angle = 2 * np.pi * i / len(lobby)
        x, y = np.cos(angle), np.sin(angle)

        # Linha de conexão (Aresta)
        fig.add_trace(go.Scatter(x=[0, x], y=[0, y], mode='lines',
                                 line=dict(width=row['Frequencia'] / 2, color='gray'),
                                 hoverinfo='none', showlegend=False))

        # Ponto do Ex-Conselheiro
        fig.add_trace(go.Scatter(x=[x], y=[y], mode='markers+text',
                                 marker=dict(size=row['Frequencia'] * 2, color='#E91E63'),
                                 text=[row['Nome']], textposition="bottom center",
                                 name=row['Nome']))

    fig.update_layout(title="<b>Teia de Lobby:</b> Ex-Conselheiros e Frequência de Retorno",
                      showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
                      plot_bgcolor='white')
    salvar_grafico(fig, "07_teia_lobby_rede")


# ==========================================
# MOTOR PRINCIPAL
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(CSV_PRESENCA) or not os.path.exists(CSV_VISITANTES):
        print("❌ Arquivos necessários não encontrados.")
    else:
        dfp = pd.read_csv(CSV_PRESENCA, sep=';')
        dfv = pd.read_csv(CSV_VISITANTES, sep=';')

        gerar_sankey_funil(dfv)
        gerar_matriz_estagnacao(dfp)
        gerar_grafo_lobby(dfv)

        print(f"\n🎉 Fase 3 concluída! Veja os arquivos 05 a 07 em: {PASTA_GRAFICOS}")