import os
import pandas as pd
import unicodedata
from datetime import datetime
from tqdm import tqdm

# IMPORTAÇÕES DOS SEUS MÓDULOS
from gerenciador_io import (
    BASE_DIR, carregar_index_atas, carregar_bases_mandatos, ler_texto_pdf, verificar_pastas
)
from config_filtros import normalizar, MESES_PT
from ferramentas_matcher import (
    linha_contem_oficial, is_same_person, criar_mapa_historico, minerar_visitantes
)

CAMINHO_SAIDA_DADOS = os.path.join(BASE_DIR, "dados", "processados")
if not os.path.exists(CAMINHO_SAIDA_DADOS): os.makedirs(CAMINHO_SAIDA_DADOS)


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
    """
    Busca no mapa histórico todos os mandatos da pessoa e concatena (Opção A).
    """
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


def main():
    print("🛡️ MOTOR DE EXTRAÇÃO V88 (OBT - HISTÓRICO CONCATENADO) 🛡️")

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

                    if not nome or nome == "VAGO": continue

                    conselheiros_nomes_norm.append(nome)
                    esta_presente = False

                    for linha in linhas_norm_uteis:
                        if linha_contem_oficial(linha, nome):
                            esta_presente = True
                            break

                    if esta_presente: presentes_nesta_ata.add(nome)

                    dados_oficiais.append({
                        "Reuniao": titulo_reuniao,
                        "Data": data_reuniao,
                        "Local": local_reuniao,
                        "Arquivo": pdf_nome,
                        "Segmento": cadeira["segmento"],
                        "Orgao": nome_orgao,
                        "Cadeira": cadeira["cadeira_padronizada"],
                        "Nome": nome,
                        "Tipo": tipo,
                        "Presente": 1 if esta_presente else 0,
                        "Genero": membro.get("genero"),
                        "Cargo_Extra": membro.get("cargo_extra")
                    })

        regs_hist, regs_ext = minerar_visitantes(
            linhas_originais, conselheiros_nomes_norm, mapa_historico, periodo_str, presentes_nesta_ata
        )

        # =========================================================
        # FUSÃO INTELIGENTE: Remove duplicados na mesma ata e agrega
        # =========================================================
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

        # Enriquecer os visitantes com os dados agregados do mapa histórico
        for vis in visitantes_unicos_ata.values():
            metadados = agregar_metadados(vis["Nome_Oficial_Associado"], mapa_historico)
            vis.update(metadados)
            dados_visitantes_geral.append(vis)

    print("\n💾 Salvando arquivos CSV...")

    if dados_oficiais:
        df_oficial = pd.DataFrame(dados_oficiais)
        df_oficial = df_oficial.drop_duplicates(subset=["Arquivo", "Nome", "Cadeira"])
        df_oficial.to_csv(
            os.path.join(CAMINHO_SAIDA_DADOS, "presenca_oficial.csv"),
            index=False, sep=';', encoding='utf-8-sig'
        )
        print("✅ presenca_oficial.csv gerado.")

    if dados_visitantes_geral:
        df_visitantes = pd.DataFrame(dados_visitantes_geral)
        df_visitantes = df_visitantes.sort_values(by="Nome_na_Ata", key=lambda x: x.map(limpar_para_ordem))
        df_visitantes.to_csv(os.path.join(CAMINHO_SAIDA_DADOS, "visitantes_geral.csv"), index=False, sep=';',
                             encoding='utf-8-sig')
        print("✅ visitantes_geral.csv gerado com históricos agregados!")

    # Apaga os ficheiros antigos para evitar confusão
    for old_file in ["visitantes_historico.csv", "visitantes_externos.csv"]:
        old_path = os.path.join(CAMINHO_SAIDA_DADOS, old_file)
        if os.path.exists(old_path):
            os.remove(old_path)


if __name__ == "__main__":
    main()