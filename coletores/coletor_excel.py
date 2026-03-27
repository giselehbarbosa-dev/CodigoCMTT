import sys
import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote

# Garante que o Python encontra a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config_ambiente import (
    URL_BASE_SITE, CAMINHO_EXCEL_INDEX, DIR_REDE_INTERNA,
    COLUNAS_INDEX_BASE, REGRAS_CONSELHO
)

PAGINAS_VISITADAS = set()
DADOS_REUNIOES = {}

# Extrai o radical do domínio automaticamente (Ex: descobre "sp.gov.br" a partir do URL base)
dominio_base_parts = urlparse(URL_BASE_SITE).netloc.split('.')
RADICAL_DOMINIO = ".".join(dominio_base_parts[-3:]) if len(dominio_base_parts) >= 3 else urlparse(URL_BASE_SITE).netloc


def limpar_lixo_cms(texto):
    texto = re.sub(r'(?:Segunda|Terça|Quarta|Quinta|Sexta|Sábado|Domingo)-feira.*?\|\s*Horário[:\s\d]+', '', texto,
                   flags=re.IGNORECASE)
    return texto.strip()


def classificar_orgao(texto_combinado):
    for orgao_oficial, lista_termos in REGRAS_CONSELHO["orgaos_palavras_chave"].items():
        if any(re.search(termo, texto_combinado, re.IGNORECASE) for termo in lista_termos):
            return orgao_oficial
    return list(REGRAS_CONSELHO["orgaos_palavras_chave"].keys())[0]


def classificar_link(texto_link, contexto, url_absoluta):
    texto_busca = f"{texto_link} {contexto} {unquote(url_absoluta)}"
    is_documento = bool(re.search(r'\.(pdf|docx?|xlsx?)(?:\?.*)?$', url_absoluta, re.IGNORECASE))

    for tipo_anexo, lista_termos in REGRAS_CONSELHO["identificadores_links"].items():
        if any(re.search(termo, texto_busca, re.IGNORECASE) for termo in lista_termos):
            return tipo_anexo

    fixos = [k for k in REGRAS_CONSELHO["identificadores_links"].keys() if k in COLUNAS_INDEX_BASE]
    return fixos[-1] if fixos and is_documento else None


def validar_e_formatar_data(data_raw):
    """Filtro matemático para impedir que Decretos (ex: 54.851/2014) sejam lidos como datas."""
    try:
        partes = data_raw.replace('.', '/').replace('-', '/').split('/')
        if len(partes) != 3: return ""
        d, m, a = partes
        if len(a) == 2: a = "20" + a

        # Aceita o "XX" e formata o mês/ano
        if d.upper() == "XX":
            m, a = int(m), int(a)
            if 1 <= m <= 12 and 2000 <= a <= 2100: return f"XX/{m:02d}/{a}"
        else:
            d, m, a = int(d), int(m), int(a)
            if 1 <= d <= 31 and 1 <= m <= 12 and 2000 <= a <= 2100:
                return f"{d:02d}/{m:02d}/{a}"
    except:
        pass
    return ""


def extrair_metadados_bloco(bloco_texto, url_absoluta, texto_link):
    bloco_texto = limpar_lixo_cms(bloco_texto)
    data, horario, local = "", "", ""

    regex_data = r'\b(\d{2}[/.-]\d{2}[/.-]\d{2,4})\b'
    regex_mes_ano = r'\b(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*[/.-]\s*(\d{4})\b'

    match_data = re.search(regex_data, bloco_texto)
    match_mes_ano = re.search(regex_mes_ano, bloco_texto, re.IGNORECASE)

    if match_data:
        data = validar_e_formatar_data(match_data.group(1))
    elif match_mes_ano:
        mes_str = match_mes_ano.group(1).lower()
        ano_str = match_mes_ano.group(2)
        mapa_meses = {'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03', 'abril': '04', 'maio': '05',
                      'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 'novembro': '11',
                      'dezembro': '12'}
        data = f"XX/{mapa_meses[mes_str]}/{ano_str}"  # Usa o "XX" visível para o usuário

    match_horario = re.search(r'\b(\d{1,2}[:h](?:[0-5]\d)?\s*(?:às|-|a)\s*\d{1,2}[:h](?:[0-5]\d)?)\b', bloco_texto,
                              re.IGNORECASE)
    if match_horario: horario = match_horario.group(1).lower()

    # Puxa todas as chaves do config para virarem stop words automaticamente
    stop_words = [r"\bLink\b", r"\bClique\b", r"\bGravaç[aã]o\b", r"http", r"www", r"\bData\b", r"\bHor[aá]rio\b",
                  r"-\s*Reuni[aã]o"]
    for chave, lista_termos in REGRAS_CONSELHO["identificadores_links"].items():
        if lista_termos: stop_words.append(rf"\b{lista_termos[0][:6]}")

    pattern_stop = "|".join(stop_words)
    match_local = re.search(rf'Local:\s*(.*?)(?=\s*(?:{pattern_stop}|$))', bloco_texto, re.IGNORECASE)
    if match_local: local = match_local.group(1).strip(" -|:.,")[:150]

    texto_combinado = f"{bloco_texto} {texto_link} {unquote(url_absoluta)}".replace('_', ' ')
    orgao = classificar_orgao(texto_combinado)

    evento_padrao = list(REGRAS_CONSELHO["tipos_reuniao"].keys())[-1]
    nome_evento_base = evento_padrao
    for nome_padrao, lista_termos in REGRAS_CONSELHO["tipos_reuniao"].items():
        if any(re.search(termo, texto_combinado, re.IGNORECASE) for termo in lista_termos):
            nome_evento_base = nome_padrao
            break

    match_num = re.search(r'(?<!\d)(\d{1,3})[ªaºo](?!\d)', texto_combinado, re.IGNORECASE)
    if not match_num:
        match_num = re.search(r'(?:reuni[aã]o|ata)\s*(?:da\s*)?(?<!\d)(\d{1,3})(?!\d)(?!\s*[/.-])', texto_combinado,
                              re.IGNORECASE)

    if match_num and nome_evento_base == evento_padrao:
        nome_evento = f"{match_num.group(1)}ª {nome_evento_base}"
    else:
        nome_evento = nome_evento_base

    if data == "":
        match_data_url = re.search(r'(?:_|-|\b)(\d{2}[_.-]\d{2}[_.-]\d{2,4})(?:_|-|\b|\.)', url_absoluta)
        if match_data_url:
            data = validar_e_formatar_data(match_data_url.group(1))

    return orgao, nome_evento, data, horario, local


def encontrar_chave_existente(orgao, nome_evento, data):
    chave_exata = f"{orgao}_{nome_evento}_{data}"
    if chave_exata in DADOS_REUNIOES: return chave_exata

    for chave in DADOS_REUNIOES.keys():
        partes = chave.split('_')
        if len(partes) >= 3 and partes[0] == orgao and partes[-1] == data:
            if "extra" in nome_evento.lower() and "extra" not in chave.lower(): continue
            if "extra" not in nome_evento.lower() and "extra" in chave.lower(): continue
            return chave
    return chave_exata


def gerenciar_reuniao(chave, orgao, nome, data, horario, local):
    if chave not in DADOS_REUNIOES:
        DADOS_REUNIOES[chave] = {col: "" for col in COLUNAS_INDEX_BASE}
        DADOS_REUNIOES[chave].update({
            "Órgão": orgao, "Nome da Reunião": nome, "Data": data, "Horário": horario, "Local": local
        })
        for k in REGRAS_CONSELHO["identificadores_links"].keys():
            if k not in COLUNAS_INDEX_BASE:
                DADOS_REUNIOES[chave][k] = []
    else:
        if "ª" in nome and "ª" not in DADOS_REUNIOES[chave]["Nome da Reunião"]:
            DADOS_REUNIOES[chave]["Nome da Reunião"] = nome
        if horario and not DADOS_REUNIOES[chave]["Horário"]:
            DADOS_REUNIOES[chave]["Horário"] = horario
        if local and not DADOS_REUNIOES[chave]["Local"]:
            DADOS_REUNIOES[chave]["Local"] = local


def varrer_para_excel(url, profundidade=0):
    LIMITE_PROFUNDIDADE = 3
    url = url.split('#')[0]

    if url in PAGINAS_VISITADAS or profundidade > LIMITE_PROFUNDIDADE:
        return

    PAGINAS_VISITADAS.add(url)
    indentacao = "  " * profundidade
    print(f"{indentacao}🔍 Nível {profundidade} | A mapear: {url}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # FASE 0: SPIDER - NAVEGAÇÃO "ANTI-CLIQUE AQUI"
        for link_sub in soup.find_all('a', href=True):
            href_sub = link_sub.get('href')
            if href_sub.startswith('#'): continue

            url_filha = urljoin(url, href_sub).split('#')[0]
            texto_link = link_sub.get_text(strip=True).lower()
            texto_pai = link_sub.parent.get_text(separator=" ", strip=True).lower() if link_sub.parent else ""

            # Cerca Virtual Escalável usando o RADICAL extraído da URL
            is_internal = RADICAL_DOMINIO in urlparse(url_filha).netloc
            is_not_file = not re.search(r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar)$', url_filha, re.IGNORECASE)

            relevante = (
                    REGRAS_CONSELHO["sigla"].lower() in url_filha.lower() or
                    REGRAS_CONSELHO["sigla"].lower() in texto_pai or
                    bool(re.search(r'\b20[1-2]\d\b', texto_pai)) or
                    any(re.search(t, texto_pai, re.IGNORECASE) for t in
                        REGRAS_CONSELHO.get("palavras_navegacao_subpaginas", []))
            )

            if is_internal and is_not_file and relevante:
                varrer_para_excel(url_filha, profundidade + 1)

        # FASE 1: REGISTRADOR DE REUNIÕES "SEM LINK"
        for tag in soup.find_all(['p', 'li', 'h2', 'h3', 'h4']):
            texto_bruto = tag.get_text(separator=" ", strip=True)
            if len(texto_bruto) < 10 or len(texto_bruto) > 500: continue

            tem_data = re.search(
                r'\b(\d{2}[/.-]\d{2}[/.-]\d{2,4}|(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*[/.-]\s*\d{4})\b',
                texto_bruto, re.IGNORECASE)
            tem_evento = any(
                re.search(t, texto_bruto, re.IGNORECASE) for v in REGRAS_CONSELHO["tipos_reuniao"].values() for t in v)
            tem_orgao = any(
                re.search(t, texto_bruto, re.IGNORECASE) for v in REGRAS_CONSELHO["orgaos_palavras_chave"].values() for
                t in v)

            if tem_data and (tem_evento or tem_orgao):
                orgao, nome_evento, data, horario, local = extrair_metadados_bloco(texto_bruto, url, "")
                if data:
                    chave = encontrar_chave_existente(orgao, nome_evento, data)
                    gerenciar_reuniao(chave, orgao, nome_evento, data, horario, local)

        # FASE 2: ANEXADOR DE ARQUIVOS (Busca DOM Global)
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if not href or href.startswith('#'): continue

            url_absoluta = urljoin(url, href).split('#')[0]
            texto_link = link.get_text(strip=True)

            caixa_atual = link.parent
            textos_coletados = [caixa_atual.get_text(separator=" ", strip=True)]

            irmaos = link.find_all_previous(['p', 'li', 'h3', 'h4', 'span'], limit=6)
            for irmao in irmaos:
                t = irmao.get_text(separator=" ", strip=True)
                if 5 < len(t) < 300:
                    textos_coletados.insert(0, t)
                    if re.search(r'\b\d{2}[/.-]\d{2}[/.-]\d{2,4}\b', t) or re.search(
                            r'\b(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*[/.-]\s*\d{4}\b',
                            t, re.IGNORECASE) or "reuni" in t.lower():
                        break

            bloco_texto = " | ".join(textos_coletados)
            contexto = caixa_atual.get_text(strip=True).lower()

            tipo_link = classificar_link(texto_link, contexto, url_absoluta)
            if not tipo_link: continue

            orgao, nome_evento, data, horario, local = extrair_metadados_bloco(bloco_texto, url_absoluta, texto_link)
            if not data: continue

            chave_reuniao = encontrar_chave_existente(orgao, nome_evento, data)
            gerenciar_reuniao(chave_reuniao, orgao, nome_evento, data, horario, local)

            url_norm = url_absoluta.replace("http://", "https://").replace("www.", "")
            if tipo_link in COLUNAS_INDEX_BASE:
                DADOS_REUNIOES[chave_reuniao][tipo_link] = url_absoluta
            else:
                existentes = [u.replace("http://", "https://").replace("www.", "") for u in
                              DADOS_REUNIOES[chave_reuniao][tipo_link]]
                if url_norm not in existentes:
                    DADOS_REUNIOES[chave_reuniao][tipo_link].append(url_absoluta)

    except Exception as e:
        pass


if __name__ == "__main__":
    print("🚀 A INICIAR RASTREADOR DE LINKS MULTI-NÍVEL (SPIDER)...")
    varrer_para_excel(URL_BASE_SITE)

    linhas_tabela = []
    chaves_dinamicas = [k for k in REGRAS_CONSELHO["identificadores_links"].keys() if k not in COLUNAS_INDEX_BASE]
    maximos_dinamicos = {k: 0 for k in chaves_dinamicas}

    for chave, dados in DADOS_REUNIOES.items():
        linha = {col: dados[col] for col in COLUNAS_INDEX_BASE}
        for k_dinamica in chaves_dinamicas:
            qtd = len(dados[k_dinamica])
            if qtd > maximos_dinamicos[k_dinamica]:
                maximos_dinamicos[k_dinamica] = qtd

            nome_col = k_dinamica.replace("oes", "ão").rstrip('s')
            if "Apresentac" in k_dinamica or "Apresentaç" in k_dinamica: nome_col = "Apresentação"

            for i, link_anexo in enumerate(dados[k_dinamica]):
                linha[f"{nome_col} {i + 1}"] = link_anexo

        linhas_tabela.append(linha)

    df = pd.DataFrame(linhas_tabela)

    colunas_geradas = list(df.columns)
    colunas_ordenadas = []
    chave_link_online = list(REGRAS_CONSELHO["identificadores_links"].keys())[0]

    for col in COLUNAS_INDEX_BASE:
        if col != chave_link_online and col in colunas_geradas:
            colunas_ordenadas.append(col)

    for col in colunas_geradas:
        if col not in COLUNAS_INDEX_BASE:
            colunas_ordenadas.append(col)

    if chave_link_online in colunas_geradas:
        colunas_ordenadas.append(chave_link_online)

    df = df[colunas_ordenadas].fillna("")

    # === ORDENAÇÃO DUPLA COM TRUQUE DO "XX" ===
    # 1. Cria uma coluna temporária substituindo "XX/" por "01/" só para o motor do Pandas entender
    df['Data_Temporaria'] = df['Data'].str.replace('XX/', '01/')
    df['Data_Calendario'] = pd.to_datetime(df['Data_Temporaria'], format='%d/%m/%Y', errors='coerce')

    # 2. Ordena por Órgão e Data, e depois destrói as colunas de rascunho
    df = df.sort_values(by=['Órgão', 'Data_Calendario', 'Nome da Reunião']).drop(
        columns=['Data_Calendario', 'Data_Temporaria'])

    os.makedirs(os.path.dirname(CAMINHO_EXCEL_INDEX), exist_ok=True)
    df.to_excel(CAMINHO_EXCEL_INDEX, index=False)
    print(f"\n✅ EXCEL GERADO COM SUCESSO E ORDENADO POR ÓRGÃO E DATA:\n -> {CAMINHO_EXCEL_INDEX}")

    if DIR_REDE_INTERNA:
        caminho_rede = os.path.join(DIR_REDE_INTERNA, "index_atasCMTT.xlsx")
        os.makedirs(DIR_REDE_INTERNA, exist_ok=True)
        df.to_excel(caminho_rede, index=False)
        print(f"✅ EXCEL COPIADO PARA A REDE SMT:\n -> {caminho_rede}")