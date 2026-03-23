"""
Script de manutenção para atualizar o cache do buscador em segundo plano.
Pode ser engatilhado pelo rotina_cmtt.bat no Windows.
"""
import sys
import os
from datetime import datetime

# Garante que o script acha a raiz do projeto (onde está a pasta 'core')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Agora importa a função lá do seu app
from analisadores.app_buscador import construir_cache_novo

def rodar_atualizacao():
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando rotina automática de atualização do cache...")

    sucesso = construir_cache_novo()

    if sucesso:
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ✅ Cache atualizado com sucesso!")
    else:
        print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ❌ Falha ao atualizar o cache.")

if __name__ == "__main__":
    rodar_atualizacao()