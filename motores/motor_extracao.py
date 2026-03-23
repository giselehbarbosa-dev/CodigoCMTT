import os
import sys
import pandas as pd
import unicodedata
from datetime import datetime
from tqdm import tqdm
from thefuzz import fuzz

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importando a infraestrutura (Core)
from core import config_ambiente
from core.gerenciador_io import (
    carregar_index_atas, carregar_bases_mandatos, ler_texto_pdf, verificar_pastas
)

# Importando as ferramentas (Utils)
from utils.config_filtros import normalizar, MESES_PT
from utils.ferramentas_matcher import (
    linha_contem_oficial, criar_mapa_historico, minerar_visitantes, normalizar_fonetica
)

# Usando o caminho já blindado pelo nosso config_ambiente!
CAMINHO_SAIDA_DADOS = config_ambiente.CAMINHO_PROCESSADOS
if not os.path.exists(CAMINHO_SAIDA_DADOS):
    os.makedirs(CAMINHO_SAIDA_DADOS)

def selecionar_mandato(data_reuniao, mandatos):
    for m in mandatos:
        if m["inicio"] <= data_reuniao <= m["fim"]: return m
    mandatos.sort(key=lambda x: x["inicio"])
    for m in mandatos:
        if m["inicio"] <= data_reuniao: return m
    return None

def limpar_para_ordem(texto):
    return u"".join([c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c)]).lower()


def agregar_metadados(nome_oficial, mapa_historico):
    if not nome_oficial:
        return {"Periodo_Mandato": "", "Segmento": "", "Orgao": "", "Cadeira": "", "Funcao": "", "Genero": ""}

    nome_norm = normalizar(nome_oficial)
    detalhes = mapa_historico.get(nome_norm, [])

    def unicos(chave):
        vistos = set()
        res = []
        for d in detalhes:
            val = d.get(chave, "")
            if val and val not in vistos:
                res.append(val)
                vistos.add(val)
        return " | ".join(res)

    return {
        "Periodo_Mandato": unicos("Periodo_mandato"),
        "Segmento": unicos("Segmento"),
        "Orgao": unicos("Orgao"),
        "Cadeira": unicos("Cadeira"),
        "Funcao": unicos("Funcao"),
        "Genero": unicos("Genero")
    }

def refinar_presencas_finais(dados_oficiais):
    print("\n🕵️ Iniciando Auto-Auditoria para desempate de Falsos Positivos...")
    df = pd.DataFrame(dados_oficiais)

    # Isola apenas quem recebeu presença para analisar
    df_presentes = df[df['Presente'] == 1]

    # Agrupa por Arquivo e pelo Trecho exato da Ata lido
    # Se uma linha tem mais de 1 pessoa, temos o "Efeito Família" (Ex: Osvaldo vs Natalício)
    agrupamento = df_presentes.groupby(['Arquivo', 'Nome_na_Ata'])

    falsos_positivos_removidos = 0

    for (arquivo, trecho_ata), grupo in agrupamento:
        if len(grupo) > 1:
            scores = []
            for index, row in grupo.iterrows():
                nome_oficial = normalizar_fonetica(row['Nome'])
                trecho_limpo = normalizar_fonetica(row['Nome_na_Ata'])

                # Usa o token_set_ratio para ver qual nome tem mais aderência ao trecho
                score = fuzz.token_set_ratio(nome_oficial, trecho_limpo)
                scores.append((index, score))

            # Descobre qual foi a maior pontuação matemática
            max_score = max(scores, key=lambda x: x[1])[1]

            # Rebaixa quem teve pontuação menor (Os impostores)
            for index, score in scores:
                if score < max_score:
                    df.at[index, 'Presente'] = 0
                    df.at[index, 'Nome_na_Ata'] = "FALSO POSITIVO (Descartado na Auditoria)"
                    falsos_positivos_removidos += 1

    if falsos_positivos_removidos > 0:
        print(f"🧹 Limpeza concluída: {falsos_positivos_removidos} 'fantasmas' removidos por desempate fonético!")

    return df.to_dict('records')  # Devolve a lista limpa para o Motor salvar


def main():
    print("🛡️ MOTOR DE EXTRAÇÃO V90 (ARRASTÃO + AUDITORIA + MANDATO NO OFICIAL) 🛡️")

    if not verificar_pastas(): return

    index_atas = carregar_index_atas()
    mandatos = carregar_bases_mandatos()

    if not index_atas or not mandatos:
        print("❌ Dados insuficientes (Index ou Mandatos vazios).")
        return

    mapa_historico = criar_mapa_historico(mandatos)

    dados_oficiais = []
    dados_visitantes_geral = []

    print(f"📂 Processando {len(index_atas)} atas...")

    for pdf_nome, info in tqdm(index_atas.items(), desc="Lendo PDFs e Extraindo Dados"):
        try:
            data_reuniao = datetime.strptime(info["data_correta"], "%d/%m/%Y")
        except Exception:
            continue

        caminho_pdf = info.get("caminho_absoluto", pdf_nome)
        titulo_reuniao = info.get("titulo_reuniao", "Não Informado")
        local_reuniao = info.get("local", "Não Informado")

        mandato_ativo = selecionar_mandato(data_reuniao, mandatos)
        if not mandato_ativo: continue

        ini_str = f"{mandato_ativo['inicio'].year}{MESES_PT[mandato_ativo['inicio'].month]}"
        fim_str = f"{mandato_ativo['fim'].year}{MESES_PT[mandato_ativo['fim'].month]}"
        periodo_str = f"{ini_str}_{fim_str}"

        linhas_originais = ler_texto_pdf(caminho_pdf)

        linhas_norm_uteis = []
        for l in linhas_originais:
            linha_norm = normalizar(l)
            if "composicao do conselho" in linha_norm or "anexo i" in linha_norm or "membros nomeados" in linha_norm:
                break
            linhas_norm_uteis.append(linha_norm)

        if not linhas_norm_uteis: continue

        conselheiros_nomes_norm = []
        presentes_nesta_ata = set()

        for cadeira in mandato_ativo["dados"]["cadeiras"]:
            nome_orgao = cadeira.get("nome_orgao_exibicao", "Não Informado")

            for tipo, lista in [("TITULAR", cadeira.get("titulares", [])), ("SUPLENTE", cadeira.get("suplentes", []))]:
                for membro in lista:
                    nome = membro.get("nome", "")

                    if not nome: continue  # Só pula se vier 100% vazio por erro

                    esta_presente = False
                    trecho_encontrado = ""

                    # SE NÃO FOR VAGO, ELE TENTA ACHAR NO PDF
                    if nome != "VAGO":
                        conselheiros_nomes_norm.append(nome)

                        for linha in linhas_norm_uteis:
                            achou, trecho = linha_contem_oficial(linha, nome)
                            if achou:
                                esta_presente = True
                                trecho_encontrado = trecho
                                break

                        if esta_presente: presentes_nesta_ata.add(nome)

                    # ADICIONA NO CSV OFICIAL (Mesmo se for VAGO, para garantir a cadeira no relatório!)
                    dados_oficiais.append({
                        "Reuniao": titulo_reuniao,
                        "Data": data_reuniao,
                        "Local": local_reuniao,
                        "Arquivo": pdf_nome,
                        "Periodo_Mandato": periodo_str,
                        "Segmento": cadeira["segmento"],
                        "Orgao": nome_orgao,
                        "Cadeira": cadeira["cadeira_padronizada"],
                        "Nome": nome,
                        "Nome_na_Ata": trecho_encontrado,
                        "Tipo": tipo,
                        "Presente": 1 if esta_presente else 0,
                        "Genero": membro.get("genero"),
                        "Cargo_Extra": membro.get("cargo_extra")
                    })

        regs_hist, regs_ext = minerar_visitantes(
            linhas_originais, conselheiros_nomes_norm, mapa_historico, periodo_str, presentes_nesta_ata
        )

        visitantes_unicos_ata = {}

        for r in regs_hist:
            nome_ata = r["Nome_Original"]
            if nome_ata not in visitantes_unicos_ata:
                visitantes_unicos_ata[nome_ata] = {
                    "Arquivo": pdf_nome,
                    "Data": data_reuniao,
                    "Reuniao": titulo_reuniao,
                    "Local": local_reuniao,
                    "Nome_na_Ata": nome_ata,
                    "Tipo_Visitante": "Ex-Conselheiro (Histórico Confirmado)",
                    "Nome_Oficial_Associado": nome_ata
                }

        for r in regs_ext:
            nome_ata = r["Nome"]
            if nome_ata not in visitantes_unicos_ata:
                visitantes_unicos_ata[nome_ata] = {
                    "Arquivo": pdf_nome,
                    "Data": data_reuniao,
                    "Reuniao": titulo_reuniao,
                    "Local": local_reuniao,
                    "Nome_na_Ata": nome_ata,
                    "Tipo_Visitante": r["Tipo"],
                    "Nome_Oficial_Associado": r.get("Nome_Associado", "")
                }

        for vis in visitantes_unicos_ata.values():
            metadados = agregar_metadados(vis["Nome_Oficial_Associado"], mapa_historico)
            vis.update(metadados)
            dados_visitantes_geral.append(vis)

    print("\n💾 Salvando arquivos CSV...")

    if dados_oficiais:
        # A MÁGICA ACONTECE AQUI: Passamos a base pelo Juiz de Desempate!
        dados_oficiais_limpos = refinar_presencas_finais(dados_oficiais)

        df_oficial = pd.DataFrame(dados_oficiais_limpos)
        df_oficial = df_oficial.drop_duplicates(subset=["Arquivo", "Nome", "Cadeira"])

        colunas_ordem = ["Reuniao", "Data", "Local", "Arquivo", "Periodo_Mandato", "Segmento", "Orgao", "Cadeira",
                         "Nome", "Nome_na_Ata", "Tipo", "Presente", "Genero", "Cargo_Extra"]
        df_oficial = df_oficial[colunas_ordem]

        # Salvando usando o GPS Mágico!
        df_oficial.to_csv(
            config_ambiente.CAMINHO_CSV_PRESENCA,
            index=False, sep=';', encoding='utf-8-sig'
        )
        print(f"✅ {config_ambiente.NOME_CSV_PRESENCA} gerado (Auditado e Refinado!).")

    if dados_visitantes_geral:
        df_visitantes = pd.DataFrame(dados_visitantes_geral)
        df_visitantes = df_visitantes.sort_values(by="Nome_na_Ata", key=lambda x: x.map(limpar_para_ordem))

        # Salvando usando o GPS Mágico!
        df_visitantes.to_csv(
            config_ambiente.CAMINHO_CSV_VISITANTES,
            index=False, sep=';', encoding='utf-8-sig'
        )
        print(f"✅ {config_ambiente.NOME_CSV_VISITANTES} gerado com históricos agregados!")

if __name__ == "__main__":
    main()