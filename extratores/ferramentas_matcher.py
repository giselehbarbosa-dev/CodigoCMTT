import re
import difflib
import unicodedata
import spacy
import itertools
from thefuzz import fuzz
from config_filtros import normalizar, contem_lixo_visual, MESES_PT

try:
    nlp = spacy.load("pt_core_news_sm")
except OSError:
    print("⚠️ ERRO: Modelo do spaCy não encontrado.")

# ==========================================
# 1. AS LISTAS DE BLOQUEIO INTELIGENTES
# ==========================================

PREFIXOS_BLOQUEIO = (
    "abert", "abraç", "acess", "agradec", "ambient", "apresent", "aprov", "aproveit", "assessor", "associa",
    "atend", "auditori", "avaliac", "avenid", "balancet", "benefici", "biciclet", "bilhet", "boletin", "cadunic",
    "calcul", "calendari", "cert", "ciclov", "civil", "cidad", "clinic", "colegi", "coletiv", "comissa", "comite",
    "comod", "comuni", "composica", "comunica", "concord", "conferenc", "conselh", "considera", "consumid", "convid",
    "convit", "coorden", "cooper", "corajos", "corbucc", "corret", "cozinh", "critic", "cultur", "debat", "declaraca",
    "deficienc", "demanda", "denunci", "departament", "deputad", "desafi", "desculp", "descrica", "desenvolviment",
    "diari", "direto", "divers", "doutor", "educac", "eleic", "eleitor", "eletronic", "empres", "engenhar", "equipament",
    "errad", "esclareciment", "escol", "esport", "esquec", "estad", "estat", "estrateg", "estud", "exempl", "executiv",
    "expans", "express", "faculdad", "fatalidad", "fazend", "ferrament", "financ", "frot", "gentilez", "gerenc", "gesta",
    "gratuidad", "habitac", "hospit", "implantaca", "inclusa", "inflaca", "inform", "institucion",
    "institut", "inter", "justic", "legend", "liberd", "licenci", "licitac", "livr", "link", "logistic", "manutenca",
    "margin", "membr", "mentir", "metodologi", "metropolitan", "metrovia", "microonib", "mini", "modernizaca", "moto",
    "moviment", "munic", "obrigad", "observador", "observatori", "onibu", "opera", "orcament", "orga", "palavr",
    "participa","passag", "paulist", "paut", "pedestr", "perfeit", "pergunt", "perimetr", "perspectiv", "planejament",
    "plenari","polici", "poluica", "pont", "prac", "prefeit", "presid", "previsa", "prezad", "privad", "procediment",
    "procurador", "prof", "program", "projet", "promoca", "promotor", "propositiv", "prosper", "public", "quadr",
    "rapid", "realment", "recomenda", "reduca", "region", "regiment", "regulamentaca", "relator", "remuneraca",
    "representant", "resoluca", "respond", "respost", "ressalv", "resultad", "resum", "reunia", "reveillon",
    "rodizi", "saud", "secretar", "seguranc", "senador", "segur", "senhor", "sindicat", "sistem", "sociedad",
    "sub", "sugesta", "super", "suplent", "tarif", "taxi", "tecnic", "tematic", "tent", "termin", "titular",
    "transit", "transport", "turism", "uber", "universidad", "urban", "usuari", "veicul", "velocidad", "verdad",
    "vereador", "verific", "viadut", "viari", "vias", "visao", "visitant"
)

TERMOS_EXATOS = set([
    "abc", "abd", "abraciclo", "absurdo", "acompanho", "alega", "ambiente", "antp", "aricanduva", "artesp", "audiencia"
    "bairro", "berrini", "biogas", "brasil", "butanta", "cades", "camara", "camera", "capelinha", "centro", "cet",
    "cid", "ciclocidade", "cmtt", "cmpu", "cnpu", "coab", "cocaia", "cohab", "companhia", "consumidor", "contran",
    "cptm", "crc", "cupece", "dados", "decoro", "denatran", "detran", "dtp", "emtt", "emtu", "escola", "esporte", "faculdade",
    "fazenda", "financas", "forum", "frota", "fundacao", "gabinete", "gigantesca", "gratuidade", "grupo", "guaianases",
    "hospital", "ibirapuera", "idec", "idosos", "iguatemi", "iii", "imirim", "infraestrutura", "instituto", "ipiranga",
    "itaquera", "jabaquara", "jacana", "justica", "justo", "lapa", "lazer", "legenda", "lei", "leste",
    "local", "logica", "logistica", "logradouro", "marginal", "marketing", "meio", "metro", "microonibus", "norte",
    "obras", "oeste", "oms", "ong", "ongs", "onu", "parabens", "parelheiros", "passe", "pirajussara", "pirituba",
    "programa", "prouni", "rede", "regiao", "resumo", "rio de janeiro", "tiete", "sampape", "sapopemba", "simtetaxis",
    "sinalisa", "sintetaxis", "smdhc", "smdu","sindimotosp", "smt", "sp", "sptrans", "spurbanuss", "sul", "sumare",
    "tarifa", "tatuape", "taxi", "taxis","tecnico", "tiete", "trem", "tremembe", "unico", "usp", "vamos", "vai",
    "verde", "vermelha", "vida", "zona"
])

PALAVRAS_BLOQUEIO = set([
    "agora", "algo", "alguem", "ali", "amanha", "ante", "apenas", "apos", "aqui", "aquilo", "assim",
    "ate", "bacana", "bastante", "beleza", "boa", "bola", "bom", "cada", "capa", "cara", "caso", "cedo",
    "chat", "cita", "claro", "comecei", "como", "conforme", "consoante", "contra", "cop", "def", "deficiencia", "dersa",
    "desde", "dia", "digo", "disse", "diz", "doc", "duvida", "ela", "elas", "ele", "eles", "elogio", "embora",
    "emo", "encaro", "enem", "entao", "entre", "epi", "essa", "esse", "esta", "este", "exato", "fala", "falei",
    "falo", "falou", "fato", "favor", "fies", "fim", "fip", "foi", "folha", "fora", "forma", "fui", "gente", "govern",
    "gt", "hoje", "ideia", "idoso", "inclusive", "isso", "jeito", "joia", "lado", "legal", "licenca", "logo", "mac",
    "mais","maneira", "mano", "mas", "menos", "meu", "minha", "mobilidade", "moca", "moco", "modo", "muito", "nada", "nao", "ninguem",
    "noite", "nossa", "nosso", "nox", "oab", "obs", "oct", "ods", "oi", "ola", "onde", "ontem", "opa", "opiniao", "osc",
    "oso", "para", "parte", "pec", "perante", "perdao", "pmi", "pois", "ponto", "por", "porque", "portanto",
    "pouco", "poxa", "puc", "qual", "quando", "quanto", "que", "quem", "questao", "racial", "sa", "salvo", "segundo",
    "sel", "sem", "seu", "show", "sim", "sinto", "sob", "sobre", "somente", "sua", "tac", "tacs", "talvez",
    "tarde", "tchau", "teg", "tipo", "tudo", "umes", "umps", "usb", "valeu", "varios", "velho", "vista",
    "voce", "voces", "vou", "wni", "wri", "youtube", "zap", "zero",
    "pessoa", "pedestre", "ciclista"
])

TITULOS_REMOVER = set([
    "arq", "av", "cmtt", "ct", "dr", "dra", "dras", "drs", "eng", "ex", "juiz", "juiza", "rua", "ruas",
    "sr", "sra", "sras", "srs"
])

PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "é"}


# ==========================================
# 2. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==========================================

def limpar_sujeira_basica(texto):
    for corte in ["Cargo:", "Organização:", "Nome:", "Assunto:", "Programação:", "Votação:", "Pauta:",
                  "Encaminhamentos:", "Horário:", "Participantes:", "Visitantes:"]:
        if corte in texto:
            texto = texto.split(corte)[-1]
    texto_limpo = texto

    separadores = [' – ', ' - ', '(', '–', '...', '. ']
    for sep in separadores:
        if sep in texto_limpo: texto_limpo = texto_limpo.split(sep)[0]

    texto_limpo = texto_limpo.strip(" :.,-;|/\\\"”“'")
    partes = texto_limpo.split()
    if not partes: return ""

    def norm(t):
        if not isinstance(t, str): return ""
        nfkd = unicodedata.normalize('NFKD', t)
        t = u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
        return re.sub(r'[^\w\s]', '', t).strip()

    while partes and (norm(partes[0]) in TITULOS_REMOVER | PREPOSICOES):
        partes.pop(0)
    while partes and (norm(partes[-1]) in TITULOS_REMOVER | PREPOSICOES):
        partes.pop()

    texto_limpo = " ".join(partes)
    texto_limpo = re.sub(r'^[^\w\sÀ-ÿ]+|[^\w\sÀ-ÿ]+$', '', texto_limpo).strip()
    return texto_limpo


def eh_sigla_ou_lixo(texto):
    tem_vogal = bool(re.search(r'[aeiouyà-ú]', texto, re.IGNORECASE))
    if not tem_vogal: return True
    if re.search(r'[bcdfghjklmnpqrstvwxzç]{4,}', texto, re.IGNORECASE): return True
    return False


def contem_letras_repetidas(texto):
    if re.search(r'([a-zA-Z])\1{2,}', texto, re.IGNORECASE): return True
    return False


def normalizar_fonetica(texto):
    t = normalizar(texto)
    t = t.replace('y', 'i')
    t = t.replace('ph', 'f')
    t = t.replace('th', 't')
    t = re.sub(r'([bcdfghjklmnpqrstvwxz])\1+', r'\1', t)
    return t


# ==========================================
# 3. LÓGICA DE CRUZAMENTO (CONSELHEIROS)
# ==========================================

def get_single_word_match(word, lista_oficiais, mapa_historico):
    w_norm = normalizar_fonetica(word)
    # IGNORA LETRAS SOLTAS COMO 'A' ou 'B' para não criar "Possíveis Conselheiros" bizarros
    if len(w_norm) <= 2: return "", False

    melhor_score = 0
    melhor_nome = ""
    is_active = False
    ignore_tokens = {"de", "da", "do", "das", "dos", "e"}

    def calcular_score_seguro(alvo, off_token):
        if off_token in ignore_tokens or len(off_token) <= 2: return 0
        if off_token == alvo: return 100
        # Permite nomes curtos (Ana, Chris) darem match com os originais!
        if len(alvo) > 2 and off_token.startswith(alvo): return 100
        return fuzz.ratio(alvo, off_token)

    for off in lista_oficiais:
        off_norm = normalizar_fonetica(off)
        for token in off_norm.split():
            score = calcular_score_seguro(w_norm, token)
            if score >= 85 and score > melhor_score:
                melhor_score = score
                melhor_nome = off
                is_active = True

    for nome_hist_norm, detalhes in mapa_historico.items():
        nome_real = detalhes[0]["Nome_Original"]
        off_norm = normalizar_fonetica(nome_hist_norm)
        for token in off_norm.split():
            score = calcular_score_seguro(w_norm, token)
            if score >= 85 and score > melhor_score:
                melhor_score = score
                melhor_nome = nome_real
                is_active = False

    return melhor_nome, is_active


def linha_contem_oficial(linha_pdf, nome_oficial):
    if nome_oficial == "VAGO": return False, ""

    linha_norm = normalizar_fonetica(linha_pdf)
    off_norm = normalizar_fonetica(nome_oficial)
    ignore_tokens = {"de", "da", "do", "das", "dos", "e"}

    linha_tokens = [t for t in linha_norm.split() if t not in ignore_tokens]
    off_tokens = [t for t in off_norm.split() if t not in ignore_tokens and len(t) > 2]

    if not off_tokens: return False, ""
    total_validos = len(off_tokens)

    def verificar_bloco_exato(bloco_tokens):
        matches = 0
        for bt in bloco_tokens:
            best_score = max([fuzz.ratio(bt, lt) for lt in linha_tokens] + [0])
            if best_score >= 80: matches += 1
        return matches == len(bloco_tokens)

    # 1. Nomes curtos (Ex: Cristiane Santos) -> Exige 100% para não alucinar com sobrenomes soltos
    if total_validos <= 2:
        if verificar_bloco_exato(off_tokens):
            return True, linha_pdf.strip()

    # 2. O ARRASTÃO: Testa todas as combinações possíveis de 2 ou mais nomes
    else:
        for tamanho in range(total_validos, 1, -1):
            for combinacao in itertools.combinations(off_tokens, tamanho):
                if verificar_bloco_exato(list(combinacao)):
                    return True, linha_pdf.strip()

    return False, ""


def is_same_person(cand_bruto, off_bruto):
    if off_bruto == "VAGO" or cand_bruto == "VAGO": return False

    cand_norm = normalizar_fonetica(cand_bruto)
    off_norm = normalizar_fonetica(off_bruto)

    cand_tokens = cand_norm.split()
    off_tokens = off_norm.split()

    if not cand_tokens or not off_tokens: return False

    # Nomes únicos vão para o get_single_word_match
    if len(cand_tokens) <= 1:
        return False

    matches = 0
    for ct in cand_tokens:
        best_score = 0
        for ot in off_tokens:
            # 1. Match Perfeito
            if ct == ot:
                score = 100
            # 2. REGRA DAS INICIAIS: Resolve "J.B" -> "Jovart Bueno"
            elif len(ct) <= 2 and ot.startswith(ct):
                score = 100
            # 3. REGRA DOS APELIDOS: Resolve "Carol" -> "Carolina" e "Chris" -> "Christina"
            elif len(ct) > 2 and ot.startswith(ct):
                score = 100
            # 4. Matemática Tradicional (Resolve erros de digitação leves)
            else:
                score = fuzz.ratio(ct, ot)

            if score > best_score:
                best_score = score

        if best_score >= 75:
            matches += 1

    # Se TODAS as palavras ou iniciais da ata baterem com o nome oficial, é a mesma pessoa!
    if matches == len(cand_tokens):
        return True

    return False


def criar_mapa_historico(mandatos):
    mapa = {}
    for m in mandatos:
        ini_str = f"{m['inicio'].year}{MESES_PT[m['inicio'].month]}"
        fim_str = f"{m['fim'].year}{MESES_PT[m['fim'].month]}"
        periodo_str = f"{ini_str}_{fim_str}"
        for cad in m["dados"]["cadeiras"]:
            segmento = cad.get("segmento", "")
            nome_cad = cad.get("cadeira_padronizada", "")
            orgao = cad.get("nome_orgao_exibicao", "Não Informado")
            for tipo, lista in [("TITULAR", cad.get("titulares", [])), ("SUPLENTE", cad.get("suplentes", []))]:
                for membro in lista:
                    nome = membro.get("nome", "")
                    genero = membro.get("genero", "")
                    if nome and nome != "VAGO":
                        norm = normalizar(nome)
                        if norm not in mapa: mapa[norm] = []
                        mapa[norm].append({
                            "Nome_Original": nome,
                            "Periodo_mandato": periodo_str,
                            "Segmento": segmento,
                            "Orgao": orgao,
                            "Cadeira": nome_cad,
                            "Funcao": tipo,
                            "Genero": genero
                        })
    return mapa


def verificar_presenca_fuzzy(nome_alvo, linha_norm, limite=85):
    if not nome_alvo: return False
    alvo_tratado = normalizar(nome_alvo)
    if alvo_tratado in linha_norm: return True
    if fuzz.token_set_ratio(alvo_tratado, linha_norm) >= limite: return True
    return False


def parece_lixo_gramatical(texto):
    if 'nlp' not in globals(): return False
    doc = nlp(texto)
    for token in doc:
        if token.pos_ in ["VERB", "ADV", "PRON"]:
            return True
    if len(doc) == 1 and doc[0].pos_ == "ADJ":
        return True
    return False


def minerar_visitantes(linhas_originais, conselheiros_do_mandato_nomes, mapa_historico, periodo_atual_str,
                       presentes_oficiais):
    registros_historicos = []
    visitantes_externos = []
    processados_hist = set()
    processados_ext = set()
    candidatos_brutos = set()

    for linha in linhas_originais:
        fragmentos = re.split(r'\s*,\s*|\b\s+e\s+\b|\s*;\s*', linha)
        for frag in fragmentos:
            frag_limpo = limpar_sujeira_basica(frag)
            if len(frag_limpo) < 3: continue

            palavras = frag_limpo.split()
            if 1 <= len(palavras) <= 5:
                eh_nome_potencial = True
                for p in palavras:
                    if p.lower() in PREPOSICOES: continue
                    if not p[0].isupper():
                        eh_nome_potencial = False;
                        break
                if eh_nome_potencial:
                    candidatos_brutos.add(frag_limpo)

            if 'nlp' in globals() and len(palavras) > 5:
                doc = nlp(frag_limpo)
                for ent in doc.ents:
                    if ent.label_ == "PER": candidatos_brutos.add(ent.text.strip(" :.,-;|/\\\"”“'"))

    oficiais_brutos = conselheiros_do_mandato_nomes

    for cand in candidatos_brutos:
        cand_norm = normalizar(cand)
        palavras = cand_norm.split()

        if contem_lixo_visual(cand) or eh_sigla_ou_lixo(cand) or contem_letras_repetidas(cand): continue
        if len(palavras) > 5: continue
        if parece_lixo_gramatical(cand): continue

        if cand_norm.startswith("sao ") or cand_norm.startswith("santo ") or cand_norm.startswith("santa "):
            continue

        bloqueado = False
        for p in palavras:
            p_norm = normalizar(p)
            if p_norm in TERMOS_EXATOS or p_norm in PALAVRAS_BLOQUEIO:
                bloqueado = True;
                break
            if any(p_norm.startswith(prefix) for prefix in PREFIXOS_BLOQUEIO):
                bloqueado = True;
                break
        if bloqueado: continue

        eh_oficial = False
        for c_oficial in oficiais_brutos:
            if is_same_person(cand, c_oficial):
                eh_oficial = True;
                break
        if eh_oficial: continue

        tipo_visitante = "Visitante Externo"
        nome_associado = ""

        match_hist = False
        for nome_hist_norm, detalhes in mapa_historico.items():
            if is_same_person(cand, nome_hist_norm):
                nome_real = detalhes[0]["Nome_Original"]
                tipo_visitante = "Ex-Conselheiro (Histórico)"

                if nome_real in presentes_oficiais:
                    match_hist = True;
                    break

                eh_ativo_agora = any(d["Periodo_mandato"] == periodo_atual_str for d in detalhes)
                if not eh_ativo_agora and nome_real not in processados_hist:
                    for d in detalhes:
                        registros_historicos.append(d)
                    processados_hist.add(nome_real)
                match_hist = True;
                break

        if match_hist: continue

        if len(palavras) == 1:
            match_unico_nome, match_ativo = get_single_word_match(cand, oficiais_brutos, mapa_historico)
            if match_unico_nome:
                nome_associado = match_unico_nome
                if match_ativo:
                    tipo_visitante = "Possível Conselheiro (Nome Único)"
                else:
                    tipo_visitante = "Possível Ex-Conselheiro (Nome Único)"
            else:
                tipo_visitante = "Visitante Externo"

        if cand not in processados_ext:
            visitantes_externos.append({
                "Nome": cand,
                "Tipo": tipo_visitante,
                "Nome_Associado": nome_associado
            })
            processados_ext.add(cand)

    visitantes_externos_finais = []
    for ve in visitantes_externos:
        nome_ext = ve["Nome"]
        vazou = False
        for c_oficial in oficiais_brutos:
            if is_same_person(nome_ext, c_oficial):
                vazou = True;
                break
        if vazou: continue
        for nome_hist_norm, detalhes in mapa_historico.items():
            if is_same_person(nome_ext, nome_hist_norm):
                nome_real = detalhes[0]["Nome_Original"]
                if nome_real not in presentes_oficiais and nome_real not in processados_hist:
                    eh_ativo_agora = any(d["Periodo_mandato"] == periodo_atual_str for d in detalhes)
                    if not eh_ativo_agora:
                        for d in detalhes:
                            registros_historicos.append(d)
                        processados_hist.add(nome_real)
                vazou = True;
                break

        if not vazou:
            visitantes_externos_finais.append(ve)

    return registros_historicos, visitantes_externos_finais