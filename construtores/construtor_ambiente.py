import os
import json
import sys

# Garante que encontra a pasta 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.config_ambiente import REGRAS_CONSELHO, CAMINHO_CONFIGS, MAPA_REDE_INTERNA

def construir_pastas_e_arquivos():
    print("🏗️ A iniciar a construção do ambiente estrutural...")

    # 1. Constrói o JSON do Perfil do Conselho
    caminho_json = os.path.join(CAMINHO_CONFIGS, "perfil_conselho.json")
    os.makedirs(CAMINHO_CONFIGS, exist_ok=True)
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(REGRAS_CONSELHO, f, ensure_ascii=False, indent=4)
    print(f"✅ Ficheiro de perfil JSON atualizado: {caminho_json}")

    # 2. Constrói as Pastas da Rede Interna dinamicamente
    if MAPA_REDE_INTERNA:
        for orgao, caminho_pasta in MAPA_REDE_INTERNA.items():
            os.makedirs(caminho_pasta, exist_ok=True)
            print(f"✅ Pasta garantida para {orgao}: {caminho_pasta}")

if __name__ == "__main__":
    construir_pastas_e_arquivos()