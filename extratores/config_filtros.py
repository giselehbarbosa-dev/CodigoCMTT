import re
import unicodedata
from datetime import datetime

# ==========================================
# CONSTANTES DE DATAS
# ==========================================
MESES_PT = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun", 7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
MESES_ABREV = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

# ==========================================
# FERRAMENTAS BASE (SEM LÓGICA DE NEGÓCIO)
# ==========================================
def normalizar(texto):
    if not isinstance(texto, str): return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    texto = u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def contem_lixo_visual(texto):
    if re.search(r'[0-9]', texto): return True
    if re.search(r'[!@#$%^&*()_=+\[\]{};\'"<>/?|\\~]', texto): return True
    if len(texto.replace(".", "")) <= 2: return True
    return False

def converter_periodo_em_datas(nome_arquivo):
    nome = nome_arquivo.lower()
    match1 = re.findall(r"([a-z]{3})(\d{4})", nome)
    match2 = re.findall(r"(\d{4})([a-z]{3})", nome)
    try:
        if len(match1) >= 2:
            return datetime(int(match1[0][1]), MESES_ABREV[match1[0][0]], 1), datetime(int(match1[1][1]), MESES_ABREV[match1[1][0]], 28)
        elif len(match2) >= 2:
            return datetime(int(match2[0][0]), MESES_ABREV[match2[0][1]], 1), datetime(int(match2[1][0]), MESES_ABREV[match2[1][1]], 28)
    except Exception:
        pass
    return datetime.min, datetime.min