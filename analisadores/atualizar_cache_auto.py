# analisadores/atualizar_cache_auto.py
import sys
import os
from datetime import datetime

# Adiciona a raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app_buscador import construir_cache_novo  # Importa a função do seu app


def rodar_atualizacao():
    print(f"[{datetime.now()}] Iniciando rotina automática de atualização do cache...")

    sucesso = construir_cache_novo()

    if sucesso:
        print(f"[{datetime.now()}] ✅ Cache atualizado com sucesso!")
    else:
        print(f"[{datetime.now()}] ❌ Falha ao atualizar o cache.")


if __name__ == "__main__":
    rodar_atualizacao()