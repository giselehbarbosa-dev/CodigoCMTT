import os
import json
import re
import pandas as pd
from datetime import datetime
import unicodedata

BASE_DIR = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo"
CAMINHO_CONFIGS = os.path.join(BASE_DIR, "dados", "base_dados")
CAMINHO_SAIDA_JSON = os.path.join(CAMINHO_CONFIGS, "index_atas.json")
CAMINHO_ARQUIVO_EXCEL = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo\dados\base_dados\index_atasCMTT.xlsx"
CAMINHO_PDFS = r"C:\Users\m124712\OneDrive - rede.sp\Documentos\CMTT\Codigo\dados\base_dados\pdf_atas_pleno"

if not os.path.exists(CAMINHO_CONFIGS): os.makedirs(CAMINHO_CONFIGS)


def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')


def extrair_numero_do_pdf(nome_arquivo):
    match = re.match(r'^0*(\d+)[_-]', nome_arquivo)
    if match: return int(match.group(1))
    return None


def normalizar_data(data_str):
    if not isinstance(data_str, str): data_str = str(data_str)
    limpo = re.sub(r'(?i)data:|em:|dia:', '', data_str).split()[0].strip().rstrip('.,')
    for fmt in ["%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]:
        try:
            return datetime.strptime(limpo, fmt)
        except:
            pass
    return None


def extrair_titulo_curto(titulo_completo):
    match1 = re.search(r'(?i)(\d+(?:ª|a|º|o)?)\s*\.?\s*(reuni[aã]o\s*(?:ordin[aá]ria|extraordin[aá]ria))',
                       titulo_completo)
    if match1:
        numero = match1.group(1).lower().replace("º", "ª").replace("o", "ª")
        if numero.isdigit(): numero += "ª"
        texto = match1.group(2).title()
        return f"{numero} {texto}"
    match2 = re.search(r'(?i)(reuni[aã]o\s*(?:extraordin[aá]ria|t[eé]cnica\s*ordin[aá]ria|t[eé]cnica))',
                       titulo_completo)
    if match2: return match2.group(1).title()
    return titulo_completo


def processar_index_excel():
    print("🕵️ INICIANDO INDEXADOR (V16 - Padronização e Blindagem)...")
    if not os.path.exists(CAMINHO_ARQUIVO_EXCEL): print("❌ Excel não encontrado."); return

    todos_pdfs = [f for f in os.listdir(CAMINHO_PDFS) if f.lower().endswith('.pdf') and "ata" in f.lower()]
    mapa_pdfs_por_ano = {}
    for pdf in todos_pdfs:
        match_ano = re.search(r'(20\d{2})', pdf)
        if match_ano:
            ano = match_ano.group(1)
            if ano not in mapa_pdfs_por_ano: mapa_pdfs_por_ano[ano] = []
            mapa_pdfs_por_ano[ano].append(pdf)

    try:
        df = pd.read_excel(CAMINHO_ARQUIVO_EXCEL, sheet_name=0, header=None, dtype=str)
    except Exception as e:
        print(f"❌ Erro Excel: {e}"); return

    gabarito = {}
    pdfs_usados = set()
    reuniao_atual = {}

    for index, row in df.iterrows():
        linha_texto = " ".join([str(x).strip() for x in row if pd.notna(x) and str(x).strip() != 'nan'])
        linha_clean = normalizar_texto(linha_texto).lower()

        # Ignora a primeira linha se for cabeçalho
        if index == 0 and ("descri" in linha_clean or "titulo" in linha_clean): continue

        is_new = (re.search(r'(\d+)\s*[\.a-z]*\s*reuniao', linha_clean) or ("reuniao" in linha_clean and (
                "extra" in linha_clean or "tecnica" in linha_clean))) and "cmtt" in linha_clean

        if is_new:
            if reuniao_atual: processar_match(reuniao_atual, mapa_pdfs_por_ano, gabarito, pdfs_usados)
            reuniao_atual = {"titulo": linha_texto, "data_obj": None, "local": "Não informado"}
            continue

        if "data:" in linha_clean or "em:" in linha_clean:
            dt = normalizar_data(linha_texto)
            if dt and reuniao_atual: reuniao_atual["data_obj"] = dt

        if "local:" in linha_clean and reuniao_atual:
            reuniao_atual["local"] = re.sub(r'(?i)local:\s*', '', linha_texto).strip()

    if reuniao_atual: processar_match(reuniao_atual, mapa_pdfs_por_ano, gabarito, pdfs_usados)

    with open(CAMINHO_SAIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(gabarito, f, indent=4, ensure_ascii=False)
    print(f"🎉 Index gerado com {len(gabarito)} vínculos em: {CAMINHO_SAIDA_JSON}")


def processar_match(dados, mapa_pdfs, gabarito, pdfs_usados):
    if not dados.get("data_obj"): return
    ano, titulo = str(dados["data_obj"].year), normalizar_texto(dados["titulo"]).lower()
    if ano not in mapa_pdfs: return

    match_num = re.search(r'(\d+)\s*[\.a-z]*\s*reuniao', titulo)
    num_reuniao = int(match_num.group(1)) if match_num else None
    pdf_match = None

    for pdf in mapa_pdfs[ano]:
        if pdf in pdfs_usados: continue
        if num_reuniao and extrair_numero_do_pdf(pdf) == num_reuniao:
            if ("extra" in pdf.lower()) == ("extra" in titulo): pdf_match = pdf; break
        elif not num_reuniao:
            if "extra" in titulo and "extra" in pdf.lower(): pdf_match = pdf; break
            if "tecnica" in titulo and "tecni" in pdf.lower(): pdf_match = pdf; break

    if pdf_match:
        gabarito[pdf_match] = {
            "titulo_reuniao": extrair_titulo_curto(dados["titulo"]),
            "data_correta": dados["data_obj"].strftime("%d/%m/%Y"),
            "local": dados["local"],
            "caminho_absoluto": os.path.join(CAMINHO_PDFS, pdf_match)
        }
        pdfs_usados.add(pdf_match)


if __name__ == "__main__":
    processar_index_excel()