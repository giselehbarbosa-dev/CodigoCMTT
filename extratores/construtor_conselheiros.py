import pandas as pd
import json
import os

BASE_DIR = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"
CAMINHO_EXCEL = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo\dados\base_dados\base_mandatosCMTT.xlsx"
PASTA_SAIDA = os.path.join(BASE_DIR, "dados", "configs")

COL_FUNCAO, COL_SEGMENTO, COL_ORGAO = "FUNÇÃO", "SEGMENTO", "ÓRGÃO"
COL_PADRONIZADA, COL_NOME = "CADEIRA_PADRONIZADA", "NOME"
COL_GENERO, COL_CARGO_EXTRA = "GÊNERO", "CARGO_EXTRA"

TERMOS_IGNORAR = ["-", "NAO INDICADO", ""]
TERMOS_SEM_VOTO = ["CONVIDADO", "SECRETARIA EXECUTIVA", "APOIO ADMINISTRATIVO", "GESTÃO DO CONSELHO"]

def limpar_texto(texto):
    if pd.isna(texto) or str(texto).strip().lower() == "nan" or texto == "":
        return ""
    return " ".join(str(texto).strip().split())

def verificar_se_vota(segmento, cadeira_padronizada):
    texto_analise = (str(segmento) + " " + str(cadeira_padronizada)).upper()
    for termo in TERMOS_SEM_VOTO:
        if termo in texto_analise: return False
    return True

def processar_aba(df, nome_aba):
    mandato_data = {"arquivo_origem": nome_aba, "cadeiras": []}
    cadeiras_map = {}

    for index, linha in df.iterrows():
        segmento = limpar_texto(linha.get(COL_SEGMENTO))
        orgao_original = limpar_texto(linha.get(COL_ORGAO))
        cadeira_padrao = limpar_texto(linha.get(COL_PADRONIZADA))
        funcao = limpar_texto(linha.get(COL_FUNCAO)).upper()
        genero = limpar_texto(linha.get(COL_GENERO)).upper()
        cargo_extra = limpar_texto(linha.get(COL_CARGO_EXTRA))

        # CORREÇÃO FRENTE 1: Captura o nome. Se for vazio/NaN, guarda como "VAGO" para não sumir a cadeira!
        nome_bruto = linha.get(COL_NOME, '')
        if pd.isna(nome_bruto) or str(nome_bruto).strip() == "":
            nome = "VAGO"
        else:
            nome = str(nome_bruto).strip()

        if not orgao_original: continue
        if not cadeira_padrao: cadeira_padrao = orgao_original.upper()

        chave = (segmento, cadeira_padrao)
        if chave not in cadeiras_map:
            cadeiras_map[chave] = {
                "segmento": segmento,
                "cadeira_padronizada": cadeira_padrao,
                "nomes_orgaos_originais": set(),
                "titulares": [],
                "suplentes": []
            }

        cadeiras_map[chave]["nomes_orgaos_originais"].add(orgao_original)

        if nome.upper() not in TERMOS_IGNORAR:
            membro_obj = {
                "nome": nome,
                "genero": genero if genero else None,
                "cargo_extra": cargo_extra if cargo_extra else None,
                "funcao_original": funcao
            }
            if "SUPLENTE" in funcao:
                cadeiras_map[chave]["suplentes"].append(membro_obj)
            else:
                cadeiras_map[chave]["titulares"].append(membro_obj)

    lista_final = []
    contagem_voto = 0
    for dados in cadeiras_map.values():
        lista_orgaos = sorted(list(dados["nomes_orgaos_originais"]))
        nome_exibicao = max(lista_orgaos, key=len) if lista_orgaos else dados["cadeira_padronizada"]

        objeto_cadeira = {
            "segmento": dados["segmento"],
            "nome_orgao_exibicao": nome_exibicao,
            "aliases_orgao": lista_orgaos,
            "cadeira_padronizada": dados["cadeira_padronizada"],
            "titulares": dados["titulares"],
            "suplentes": dados["suplentes"]
        }
        lista_final.append(objeto_cadeira)
        if verificar_se_vota(dados["segmento"], dados["cadeira_padronizada"]):
            contagem_voto += 1

    mandato_data["cadeiras"] = lista_final
    return mandato_data, contagem_voto

def main():
    print("🚀 Iniciando Construtor de Conselheiros (V65 - Modular e Blindado)")
    if not os.path.exists(PASTA_SAIDA): os.makedirs(PASTA_SAIDA)
    try:
        xls = pd.ExcelFile(CAMINHO_EXCEL)
    except Exception as e:
        print(f"❌ Erro ao abrir Excel: {e}"); return

    for nome_aba in xls.sheet_names:
        if nome_aba.lower() in ["listas", "ajuda", "config", "rascunho", "checklist", "exemplo"]: continue
        try:
            df = pd.read_excel(xls, sheet_name=nome_aba)
            df.columns = [str(c).strip().upper() for c in df.columns]
            if COL_ORGAO not in df.columns: continue

            dados, n_votos = processar_aba(df, nome_aba)
            caminho_json = os.path.join(PASTA_SAIDA, f"{nome_aba}.json")
            with open(caminho_json, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            print(f"✅ JSON Gerado: {nome_aba}.json | Cadeiras com Voto: {n_votos}")
        except Exception as e:
            print(f"❌ Erro na aba {nome_aba}: {e}")

if __name__ == "__main__":
    main()