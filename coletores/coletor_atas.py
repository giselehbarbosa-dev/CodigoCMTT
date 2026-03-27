import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# -----------------------------------------------------------------------------
# SETUP DE IMPORTAÇÃO (Garante que o script ache as pastas do projeto)
# -----------------------------------------------------------------------------
# Adiciona a raiz do projeto ao sys.path para conseguirmos importar o core e utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importando o "Mapa" e a "Fonte da Verdade" do nosso projeto
from core.config_ambiente import (
    URL_BASE_SITE,
    CAMINHO_PDFS_PADRAO,
    MAPA_REDE_INTERNA
)

# Importando a sua ferramenta de limpeza de texto para tratar acentos e caracteres
from utils.config_filtros import normalizar


# -----------------------------------------------------------------------------
# MÓDULO 1: O EXTRATOR E PADRONIZADOR (PARSER)
# -----------------------------------------------------------------------------
def extrair_metadados_e_renomear(texto_bloco, texto_link):
    """
    Analisa um bloco de texto sujo do HTML do site e extrai as variáveis
    para montar o nome do arquivo no padrão estrito do projeto.
    """
    # 1. Extração do Ano
    match_ano = re.search(r"Data:.*?(\d{4})", texto_bloco, re.IGNORECASE)
    ano = match_ano.group(1) if match_ano else "0000"

    # 2. Extração do Número da Reunião (Procura dígitos antes de 'Reunião' ou 'ª')
    match_num = re.search(r"(\d+)[ªaºo]?\s*Reunião", texto_bloco, re.IGNORECASE)
    numero = match_num.group(1).zfill(2) if match_num else "00"

    # 3. Classificação do Órgão (Pleno vs Câmara Temática)
    orgao_tag = "Pleno"
    orgao_chave_dicionario = "Pleno"  # Usado para buscar no MAPA_REDE_INTERNA

    # Busca 'Câmara Temática de...', capturando o resto do nome (aceita espaços)
    match_ct = re.search(r"Câmara Temática\s+(?:de\s+)?([A-Za-zÀ-ÿ\s]+)", texto_bloco, re.IGNORECASE)
    if match_ct:
        tema_bruto = match_ct.group(1).strip()

        # O PULO DO GATO: Usa sua ferramenta para limpar acentos, põe em maiúsculas (Title) e troca espaços por '_'
        # Exemplo: "Mobilidade a Pé" -> "Mobilidade_A_Pe"
        tema_limpo = normalizar(tema_bruto).title().replace(" ", "_")

        orgao_tag = f"CT_{tema_limpo}"
        orgao_chave_dicionario = f"CT_{tema_limpo}"

    # 4. Tipo de Arquivo (Ata ou Apresentação)
    # Procuramos no texto do próprio link ou no contexto imediato
    is_apresentacao = "apresentação" in texto_link.lower() or "apresentação" in texto_bloco.lower()
    sufixo_arq = "apr" if is_apresentacao else "ata"

    # 5. Classificação do Tipo de Reunião e Montagem do Nome Padrão
    texto_lower = texto_bloco.lower()

    if "extraordinária" in texto_lower:
        nome_arquivo = f"extra_{numero}_{ano}_{orgao_tag}_{sufixo_arq}.pdf"

    elif "técnica" in texto_lower:
        nome_arquivo = f"tecni_{numero}_{ano}_{orgao_tag}_{sufixo_arq}.pdf"

    else:  # Ordinária (Padrão)
        tipo_ordin = "ordin" if orgao_tag == "Pleno" else "ord"
        nome_arquivo = f"{numero}_{ano}_{orgao_tag}_{tipo_ordin}_{sufixo_arq}.pdf"

    return nome_arquivo, orgao_chave_dicionario


# -----------------------------------------------------------------------------
# MÓDULO 2: O GERENCIADOR DE DOWNLOAD E ROTEAMENTO (DOWNLOADER)
# -----------------------------------------------------------------------------
def processar_download(url_pdf, nome_padronizado, orgao_chave):
    """
    Verifica a existência do arquivo para poupar banda. Se não existir, baixa e
    salva nos dois caminhos (Repositório e Rede Interna).
    """
    caminho_1_repo = os.path.join(CAMINHO_PDFS_PADRAO, nome_padronizado)

    # VALIDAÇÃO ANTI-DUPLICAÇÃO
    if os.path.exists(caminho_1_repo):
        print(f"⏩ IGNORADO (Já existe): {nome_padronizado}")
        return False

    print(f"⬇️ BAIXANDO: {nome_padronizado}...")
    try:
        # Baixa o PDF para a memória RAM
        resposta = requests.get(url_pdf, timeout=15)
        resposta.raise_for_status()  # Verifica se deu erro HTTP (ex: 404)

        # SALVAMENTO 1: Repositório do Código (Sempre ocorre)
        os.makedirs(CAMINHO_PDFS_PADRAO, exist_ok=True)
        with open(caminho_1_repo, 'wb') as f:
            f.write(resposta.content)
        print(f"   ✅ Salvo no Código: {caminho_1_repo}")

        # SALVAMENTO 2: Rede Interna (Roteamento Dinâmico)
        caminho_rede_orgao = MAPA_REDE_INTERNA.get(orgao_chave)
        if caminho_rede_orgao:
            os.makedirs(caminho_rede_orgao, exist_ok=True)
            caminho_2_rede = os.path.join(caminho_rede_orgao, nome_padronizado)
            with open(caminho_2_rede, 'wb') as f:
                f.write(resposta.content)
            print(f"   ✅ Salvo na Rede SMT: {caminho_2_rede}")

        return True

    except Exception as e:
        print(f"   ❌ ERRO ao baixar {url_pdf}: {e}")
        return False


# -----------------------------------------------------------------------------
# MÓDULO 3: O RASTREADOR (CRAWLER E SUBPÁGINAS)
# -----------------------------------------------------------------------------
# Um 'set' global para anotar as páginas que o robô já visitou e evitar loops infinitos
PAGINAS_VISITADAS = set()


def varrer_pagina_site(url, is_pagina_principal=True):
    """
    Acessa a URL, lê o HTML, busca links de arquivos e navega pelas subpáginas (anos anteriores).
    """
    if url in PAGINAS_VISITADAS:
        return

    PAGINAS_VISITADAS.add(url)
    print(f"\n🔍 Vasculhando URL: {url}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # =====================================================================
        # ETAPA A: PROCURAR SUBPÁGINAS (Histórico e Câmaras Temáticas)
        # =====================================================================
        if is_pagina_principal:
            todos_links = soup.find_all('a', href=True)
            for link_sub in todos_links:
                texto_sub = link_sub.get_text(strip=True).lower()
                href_sub = link_sub.get('href')

                # Regras para descobrir se o link é uma subpágina que queremos visitar:
                # 1. É um ano entre 2013 e 2029 (Ex: "2025")
                is_ano = re.match(r'^20[1-2]\d$', texto_sub)
                # 2. Ou é um botão de Câmara Temática
                is_ct = "câmara temática" in texto_sub or "camara tematica" in texto_sub

                if (is_ano or is_ct) and not re.search(r'pdf$', href_sub, re.IGNORECASE):
                    url_subpagina = urljoin(url, href_sub)
                    print(f"   🚪 Nova Subpágina Encontrada [{texto_sub}]. Entrando...")
                    varrer_pagina_site(url_subpagina, is_pagina_principal=False)

        # =====================================================================
        # ETAPA B: EXTRAIR OS ARQUIVOS DA PÁGINA ATUAL
        # =====================================================================
        links_arquivos = soup.find_all('a', href=True)

        for link in links_arquivos:
            url_pdf_relativa = link.get('href')

            # FILTRO 1: Ignora links do Teams, Youtube, etc.
            if re.search(r"(teams\.microsoft|youtube|zoom|meet)", url_pdf_relativa, re.IGNORECASE):
                continue

            # FILTRO 2: Captura rotas que terminam em pdf ou -pdf
            if not re.search(r'pdf$', url_pdf_relativa, re.IGNORECASE):
                continue

            url_pdf_absoluta = urljoin(url, url_pdf_relativa)
            texto_link = link.get_text(strip=True)

            # ESTRATÉGIA DE CONTEXTO REVERSO (Resolve o Bug do "0000" e "Bicicleta")
            # Pega os 20 fragmentos de texto imediatamente ANTES do link na página
            strings_anteriores = [s.strip() for s in link.find_all_previous(string=True) if s.strip()]
            contexto_lista = strings_anteriores[:20]
            contexto_lista.reverse()  # Coloca na ordem de leitura humana

            bloco_texto_sujo = " ".join(contexto_lista) + " " + texto_link

            # FILTRO 3: Só avança se o contexto falar de ata, apresentação ou reunião
            if not re.search(r"(ata|apresentaç|reunião)", bloco_texto_sujo, re.IGNORECASE):
                continue

            # 1. Extrai Metadados
            nome_padronizado, orgao_chave = extrair_metadados_e_renomear(bloco_texto_sujo, texto_link)

            # 2. Roteia e Baixa
            processar_download(url_pdf_absoluta, nome_padronizado, orgao_chave)

    except Exception as e:
        print(f"❌ Falha ao processar a página: {e}")


# =============================================================================
# GATILHO DE EXECUÇÃO
# =============================================================================
if __name__ == "__main__":
    from core.config_ambiente import URL_BASE_SITE  # Importação atualizada!

    print("🚀 INICIANDO COLETOR DE ATAS DO CMTT...")
    varrer_pagina_site(URL_BASE_SITE, is_pagina_principal=True)
    print("\n🏁 VARREDURA COMPLETA CONCLUÍDA.")