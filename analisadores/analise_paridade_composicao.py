"""
Módulo: Análise de Paridade e Composição (Fase 2) - Padrão Executivo
Objetivo: Gerar Dashboards Interativos (HTML) e Estáticos (PNG) usando Plotly.
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURAÇÕES E DIRETÓRIOS
# ==========================================
DIRETORIO_RAIZ = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"
PASTA_DADOS = os.path.join(DIRETORIO_RAIZ, "dados", "processados")
PASTA_GRAFICOS = os.path.join(DIRETORIO_RAIZ, "graficos")
CSV_PRESENCA = os.path.join(PASTA_DADOS, "presenca_oficial.csv")

os.makedirs(PASTA_GRAFICOS, exist_ok=True)

CORES_MACRO = {
    'Poder Público': '#2196F3',
    'Sociedade Civil': '#4CAF50',
    'Operadores/Empresarial': '#FF9800',
    'Outros': '#9E9E9E'
}

def mapear_macro_forcas(segmento):
    seg = str(segmento).upper()
    if 'SOCIEDADE CIVIL' in seg: return 'Sociedade Civil'
    elif 'OPERADORES' in seg or 'SETOR EMPRESARIAL' in seg: return 'Operadores/Empresarial'
    elif 'ÓRGÃO' in seg or 'PÚBLICO' in seg or 'MUNICIPAL' in seg: return 'Poder Público'
    return 'Outros'

def salvar_grafico(fig, nome_arquivo):
    """Salva o gráfico em formato interativo (HTML) e tenta salvar em estático (PNG)."""
    caminho_html = os.path.join(PASTA_GRAFICOS, f"{nome_arquivo}.html")
    caminho_png = os.path.join(PASTA_GRAFICOS, f"{nome_arquivo}.png")

    fig.write_html(caminho_html)

    try:
        fig.write_image(caminho_png, scale=2, width=1200, height=700)
        print(f"   ✅ Salvo: {nome_arquivo} (.html e .png)")
    except Exception:
        print(f"   ✅ Salvo: {nome_arquivo}.html")
        print(f"   ⚠️ Aviso: PNG não gerado devido ao Kaleido. Acesse o HTML para baixar a imagem.")

# ==========================================
# ANÁLISE 1: TREEMAP DE COMPOSIÇÃO DE FORÇAS
# ==========================================
def gerar_treemap_composicao(df):
    print("⏳ Gerando 1/4: Mapa de Árvore (Treemap) da Composição...")
    df_cadeiras = df.dropna(subset=['Macro Força', 'Segmento', 'Cadeira'])
    df_unicas = df_cadeiras[['Macro Força', 'Segmento', 'Cadeira']].drop_duplicates()

    fig = px.treemap(
        df_unicas,
        path=[px.Constant("CMTT (Todas as Cadeiras)"), 'Macro Força', 'Segmento', 'Cadeira'],
        color='Macro Força', color_discrete_map=CORES_MACRO,
        title="<b>Arquitetura de Poder:</b> Composição Estrutural do CMTT"
    )
    fig.update_traces(root_color="lightgrey", textinfo="label+value")
    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25), font_family="Arial")
    salvar_grafico(fig, "01_composicao_forcas_treemap")

# ==========================================
# ANÁLISE 2: RADAR DE DESIGUALDADE (GÊNERO POR MACRO FORÇA)
# ==========================================
def gerar_radar_desigualdade(df):
    print("⏳ Gerando 2/4: Radar de Desigualdade de Gênero...")
    df_genero = df[df['Genero'].isin(['F', 'M'])]
    df_unicos = df_genero.drop_duplicates(subset=['Macro Força', 'Cadeira', 'Nome', 'Genero'])

    agrupado = df_unicos.groupby(['Macro Força', 'Genero']).size().unstack(fill_value=0)
    agrupado['Total'] = agrupado['F'] + agrupado['M']
    agrupado['% Mulheres'] = (agrupado['F'] / agrupado['Total']) * 100
    agrupado = agrupado.loc[['Poder Público', 'Sociedade Civil', 'Operadores/Empresarial']]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=agrupado['% Mulheres'].tolist() + [agrupado['% Mulheres'].iloc[0]],
        theta=agrupado.index.tolist() + [agrupado.index[0]],
        fill='toself', name='Representação Feminina Atual', line_color='#E91E63'
    ))
    fig.add_trace(go.Scatterpolar(
        r=[50, 50, 50, 50], theta=agrupado.index.tolist() + [agrupado.index[0]],
        mode='lines', name='Meta Legal Paritária (50%)', line_color='black', line_dash='dash'
    ))
    fig.update_layout(
        title="<b>Radar de Paridade:</b> Aderência à Lei 15.946 por Segmento",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
        showlegend=True, font_family="Arial"
    )
    salvar_grafico(fig, "02_radar_desigualdade_genero")

# ==========================================
# ANÁLISE 3: EVOLUÇÃO PARITÁRIA COM ZONA DE META
# ==========================================
def gerar_curva_evolucao_zona_meta(df):
    print("⏳ Gerando 3/4: Curva de Evolução Paritária (Timeline)...")
    df['Ano'] = pd.to_datetime(df['Data'], errors='coerce').dt.year
    df = df.dropna(subset=['Ano'])
    df_genero = df[df['Genero'].isin(['F', 'M'])]
    df_unicos = df_genero.drop_duplicates(subset=['Ano', 'Macro Força', 'Nome', 'Genero'])

    agrupado = df_unicos.groupby(['Ano', 'Macro Força', 'Genero']).size().unstack(fill_value=0).reset_index()
    agrupado['Total'] = agrupado['F'] + agrupado['M']
    agrupado['% Mulheres'] = (agrupado['F'] / agrupado['Total']) * 100
    agrupado = agrupado[agrupado['Macro Força'].isin(['Poder Público', 'Sociedade Civil', 'Operadores/Empresarial'])]

    fig = px.line(
        agrupado, x="Ano", y="% Mulheres", color='Macro Força', markers=True,
        color_discrete_map=CORES_MACRO, title="<b>Evolução Histórica:</b> Percentual de Mulheres no Conselho"
    )
    fig.add_hrect(
        y0=50, y1=100, line_width=0, fillcolor="green", opacity=0.1,
        annotation_text="Zona de Cumprimento da Lei", annotation_position="top left"
    )
    fig.add_hline(y=50, line_dash="dash", line_color="black")
    fig.update_layout(
        yaxis_title="Proporção Feminina (%)", xaxis_title="Ano da Reunião",
        yaxis_range=[0, 105], plot_bgcolor='white', font_family="Arial"
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    salvar_grafico(fig, "03_evolucao_paritaria_timeline")

# ==========================================
# ANÁLISE 4: O GARGALO DA SUPLÊNCIA (POR MANDATO)
# ==========================================
def gerar_gargalo_suplencia_temporal(df):
    print("⏳ Gerando 4/4: Gargalo da Suplência (Evolução por Mandato)...")

    # Lemos diretamente a coluna limpa da Fase 1
    if 'Periodo_Mandato' not in df.columns:
        print("   ⚠️ AVISO: Coluna 'Periodo_Mandato' ainda não encontrada.")
        print("   ⚠️ O gráfico 4 não será gerado até que a Fase 1 atualize o CSV.")
        return

    df = df.dropna(subset=['Periodo_Mandato']).copy()

    # Limpa e filtra
    df['Tipo'] = df['Tipo'].astype(str).str.upper().str.strip()
    df_filtrado = df[df['Tipo'].isin(['TITULAR', 'SUPLENTE']) & df['Genero'].isin(['F', 'M'])]

    # Remove duplicatas baseadas no MANDATO
    df_unicos = df_filtrado.drop_duplicates(subset=['Periodo_Mandato', 'Cadeira', 'Nome', 'Tipo', 'Genero'])

    # Calcula a proporção
    agrupado = df_unicos.groupby(['Periodo_Mandato', 'Tipo', 'Genero']).size().unstack(fill_value=0).reset_index()
    agrupado['Total'] = agrupado['F'] + agrupado['M']
    agrupado['% Mulheres'] = (agrupado['F'] / agrupado['Total']) * 100

    # Gráfico de Barras Agrupadas
    fig = px.bar(
        agrupado, x="Periodo_Mandato", y="% Mulheres", color="Tipo", barmode="group",
        color_discrete_map={'TITULAR': '#1A237E', 'SUPLENTE': '#E91E63'},
        title="<b>Poder de Voto (Por Mandato):</b> Proporção de Mulheres Titulares vs. Suplentes",
        text_auto='.1f'
    )

    # Adiciona a meta paritária
    fig.add_hline(y=50, line_dash="dash", line_color="black", annotation_text="Meta Paritária (50%)")

    fig.update_layout(
        yaxis_title="Proporção de Ocupação Feminina (%)",
        xaxis_title="Ciclo de Mandato do CMTT",
        yaxis_range=[0, 105],
        plot_bgcolor='white',
        font_family="Arial",
        legend_title="Tipo de Cadeira"
    )

    salvar_grafico(fig, "04_gargalo_suplencia_mandato")

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("==========================================================")
    print("📊 INICIANDO DASHBOARDS INTERATIVOS PLOTLY (FASE 2)")
    print("==========================================================\n")

    if not os.path.exists(CSV_PRESENCA):
        print(f"❌ ERRO: Arquivo não encontrado em: {CSV_PRESENCA}")
    else:
        df_oficial = pd.read_csv(CSV_PRESENCA, sep=';')
        df_oficial['Macro Força'] = df_oficial['Segmento'].apply(mapear_macro_forcas)

        gerar_treemap_composicao(df_oficial)
        gerar_radar_desigualdade(df_oficial)
        gerar_curva_evolucao_zona_meta(df_oficial)
        gerar_gargalo_suplencia_temporal(df_oficial)

        print(f"\n🎉 SUCESSO! Dashboards gerados na pasta: {PASTA_GRAFICOS}")