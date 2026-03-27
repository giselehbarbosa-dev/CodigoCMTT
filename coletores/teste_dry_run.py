import sys
import os
import requests
import re
from bs4 import BeautifulSoup

# SETUP DE IMPORTAÇÃO
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config_ambiente import URL_BASE_SITE


def raio_x_site():
    print("===================================================================")
    print("🔬 MODO RAIO-X: BUSCANDO COMO O SITE ESCONDE OS ARQUIVOS")
    print("===================================================================\n")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(URL_BASE_SITE, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Agora pegamos TODOS os links da página (sem exigir .pdf)
        todos_os_links = soup.find_all('a')
        print(f"✅ O site carregou com um total de {len(todos_os_links)} links gerais.\n")

        encontrados = 0
        for link in todos_os_links:
            texto_link = link.get_text(strip=True)
            bloco_texto = link.parent.get_text(separator=" ", strip=True)
            href_real = link.get('href', 'SEM_HREF')

            # Procura nossas palavras-chave em qualquer lugar perto do link
            if re.search(r"(ata|apresentaç|reunião|clique aqui)", bloco_texto, re.IGNORECASE):
                encontrados += 1
                print(f"👀 TEXTO DO BOTÃO: {texto_link}")
                print(f"🔗 LINK ESCONDIDO (href): {href_real}")
                print(f"🧱 CONTEXTO: {bloco_texto[:150]}...")
                print("-" * 65)

        if encontrados == 0:
            print(
                "❌ Nenhuma ata encontrada. O site provavelmente usa JavaScript para carregar os dados (Precisaremos do Selenium).")

    except Exception as e:
        print(f"❌ Erro ao ler o site: {e}")


if __name__ == "__main__":
    raio_x_site()