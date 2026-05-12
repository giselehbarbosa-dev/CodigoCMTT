# 🏛️ Projeto CMTT - Mineração e Análise de Dados

**Documentação Oficial da Arquitetura de Extração de Identidades e Busca em Larga Escala**

O CMTT Pipeline evoluiu para um modelo de **Explainable AI (XAI)** estruturado em um framework **White-Label** implementando a moderna Arquitetura Medalhão (Camadas Bronze, Prata e Ouro). Em vez de uma caixa-preta de decisões, o sistema adota a estratégia de Alta Revogação (High Recall): ele busca todas as combinações possíveis de nomes para evitar perdas (falsos negativos), mas 'confessa' o que leu em uma coluna de auditoria, permitindo um fluxo Human-in-the-Loop para validação humana rápida e 100% segura.
🎯 **Objetivo:** Criar um pipeline automatizado e escalável capaz de ler atas em PDF do Conselho Municipal de Trânsito e Transporte (CMTT), extrair os nomes dos presentes, cruzar com a base oficial de conselheiros e classificar os participantes entre Oficiais, Históricos e Visitantes Externos, lidando com erros de digitação, lixo de chat e extração de texto sujo. Além disso, disponibilizar uma interface web de busca flexível (App Web) para consulta rápida em todo o acervo histórico.

---

## ⚙️ Pré-requisitos e Instalação (Setup)

Para garantir a reprodutibilidade do projeto em qualquer máquina, utilizamos um ambiente isolado.

**1. Instale as bibliotecas via terminal:**
```bash
pip install -r requirements.txt
```

**2. Faça o download do modelo gramatical do spaCy (em português):**
```bash
python -m spacy download pt_core_news_sm
```

**3. Configure as Variáveis de Ambiente:**
Crie um arquivo `.env` na raiz do projeto (use o `.env.example` como base) e defina seus caminhos e senhas locais. **NUNCA** suba o `.env` para repositórios públicos.

---

## 🏗️ Arquitetura do Sistema (Domain-Driven Design)

O projeto foi refatorado sob o princípio de **Separação de Responsabilidades**. Cada pasta tem um domínio único e específico, tornando o código altamente escalável.

### 🕷️ 0. A Coleta Automatizada (Fase 0 - Web Scraping)
* **`coletores/coletor_atas.py` (O Robô de Extração Web)**
  * O ponto de partida do pipeline. Responsável por minerar a matéria-prima bruta diretamente da fonte oficial.
  * **O que faz:** Acessa o portal da Prefeitura (via `requests` e `BeautifulSoup`), varre o HTML não-estruturado em busca de novas reuniões e faz o download seguro dos PDFs (Atas e Apresentações).
  * **Padronização Estrita (Renomeação Inteligente):** Elimina o caos de nomes de arquivos baixados da internet. O robô extrai os metadados do texto e renomeia os PDFs para um padrão previsível e auditável (ex: `78_2025_Pleno_ordin_ata.pdf` ou `extra_01_2015_CT_Bicicleta_ata.pdf`).
  * **Roteamento Dinâmico (Dual Save):** Salva os arquivos simultaneamente no Data Lake local (para processamento do pipeline) e na rede interna da secretaria, criando rotas dinâmicas específicas para o Conselho Pleno ou Câmaras Temáticas.
  * **Eficiência (Trava Anti-Duplicação):** Antes de realizar qualquer requisição de download, o robô verifica o ecossistema local. Se o PDF já existir na base, ele pula a etapa, economizando banda e tempo de processamento.
  * **Interface com o Sistema:** Alimenta diretamente a pasta `dados/base_dados/pdf_atas_pleno/`, entregando os arquivos limpos e mastigados para o `construtor_index.py` (Fase 1) iniciar o mapeamento.
* **`coletores/coletor_excel.py`:** Um spider web que varre as subpáginas e atualiza o mapeamento de datas e reuniões na planilha oficial.

### 📍 1. O Coração do Sistema
* **`core/config_ambiente.py`:** A Fonte Única da Verdade. Centraliza caminhos, arquivos e variáveis de nuvem. Possui auto-detecção de diretório para deploys dinâmicos.
* **`core/gerenciador_io.py` (O Bibliotecário):** Abre PDFs via `pdfplumber`, extrai textos removendo quebras de linha invisíveis do Windows e valida o ecossistema de dados.

### 🛠️ 2. A Caixa de Ferramentas Genéricas
* **`utils/config_filtros.py` (O Enfermeiro)**
  * Módulo focado exclusivamente no tratamento básico e "cego" de strings.
  * **O que faz:** Remove acentos, esmaga espaços duplos, limpa caracteres especiais e faz a conversão de strings de período (ex: "2013ago") para objetos datetime do Python.
  * **Escalabilidade:** 100% universal para qualquer texto em português.
* **`utils/ferramentas_matcher.py` (O "Cirurgião com Inteligência Artificial")**
  * O verdadeiro cérebro da operação de cruzamento de dados.
  * **O que faz:**
    * Usa a IA do `spaCy` para análise morfossintática, eliminando verbos, pronomes e advérbios soltos.
    * Usa a matemática de proximidade (`thefuzz`) para tolerar erros de digitação nos nomes.
    * Possui o "Exterminador em Loop" para decapitar preposições e títulos (Sr., Dra., Conselheira).
    * Usa Extração Inversa por Prefixos para barrar centenas de termos institucionais e lixos de chat sem bloquear nomes próprios.
    * Resolve a ambiguidade de nomes curtos (ex: "Rafael"), vasculhando os arquivos e criando a coluna `Nome_Associado` para diferenciar Conselheiros de Munícipes comuns.
    * Lógica Invertida (Anti-Fantasmas): Exige que múltiplas partes do nome oficial sejam encontradas na ata para validar a presença, erradicando falsos positivos.
    * Nova Lógica de Arrastão (N-Grams): Agora utiliza a biblioteca itertools para gerar combinações automáticas de nomes (ex: Primeiro + Último). Isso garante que o sistema capture variações como "Ana de Paula" ou "Rita Paula", mesmo que o nome oficial seja "Ana Rita de Paula".
    * Sistema de Confissão: A função de busca foi alterada para retornar não apenas o "match", mas o trecho bruto lido no PDF, alimentando a nova coluna de auditoria.

### 🏗️ 3. Os Preparadores de Terreno (Construtores)
* **`construtores/construtor_ambiente.py`:** Gera a infraestrutura de diretórios (Data Lake).
* **`construtores/construtor_index.py` (O Indexador)**
  * Mapeia o caos de arquivos e planilhas soltas.
  * **O que faz:** Lê a planilha de controle de atas, usa Expressões Regulares (RegEx) flexíveis para ignorar cabeçalhos, extrair datas/locais e criar um dicionário de gabarito (`index_atas.json`) vinculando cada PDF ao seu respectivo mandato e reunião.
* **`construtores/construtor_conselheiros.py` (O RH)**
  * Mapeia a estrutura de poder do Conselho.
  * **O que faz:** Lê a planilha oficial de mandatos do Excel, entende quem tem direito a voto, estrutura a geometria de poder, agrupando titulares e suplentes por segmento/cadeira (usando chaves compostas) e gera JSONs determinísticos e padronizados para cada mandato. Possui blindagem contra cabeçalhos mal digitados e células vazias (NaN). Possui trava de Auditoria de Vacância (assinala cadeiras sem nome como "VAGO" em vez de excluí-las).
* **`construtores/construtor_cache.py`:** O Moinho. Lê os PDFs pesados uma única vez e gera um Cérebro JSON super rápido (`.cache_corpus_atas.json`), evitando a releitura constante dos documentos pelos motores de IA.
* **`construtores/construtor_dicionario.py`:** Data Governance. O Guardião de Metadados. Lê a base oficial e gera o Catálogo_de_Metadados_CMTT.xlsx, rastreando a evolução histórica de Secretarias/Órgãos e a alocação de Titulares e Suplentes ao longo de todos os mandatos.

### 🏭 4. A Linha de Produção e Auditoria
* **`motores/motor_extracao.py` (O Maestro)**
  * O arquivo principal que orquestra todos os outros.
  * Barra de Progresso: Implementação da tqdm para monitoramento visual do tempo de processamento das atas.
  * Auditoria XAI: Injeta a coluna Nome_na_Ata no CSV oficial, permitindo conferência humana instantânea de falsos positivos.
  * **O que faz:** Roda o loop principal pelas atas, aplica táticas "Anti-Negrito" e "Anti-Anexos" na leitura, chama o matcher para separar as entidades e exporta o resultado, ordenando perfeitamente a lista alfabética e ignorando acentos. Aplica o **Bypass Ninja**: Lê o texto bruto linha a linha para curar a "cegueira" da IA em tabelas espremidas do PDF, garantindo a captura de 100% dos conselheiros presentes.
* **`motores/atualizador_bases.py` :** O Consolidador - Camada Prata. Peça-chave do ciclo Human-in-the-Loop. Lê o gabarito preenchido pela equipe de auditoria na Camada Staging, corrige presenças faltantes, remove falsos-visitantes e gera as bases _conferido.csv. Garante a Rastreabilidade Absoluta (Data Lineage) sem sobrescrever os dados lidos pela máquina.
* **`motores/motor_tematico.py` (O Termômetro de Pautas - Aplica a técnica de *Extração Inversa* (usando a base de pessoas como escudo) e minera Organizações da Sociedade Civil (OSCs) e os principais temas debatidos na ata via spaCy.)**
  * Responsável pela **Modelagem de Tópicos Estatística** e **Extração de Evidências**.
  * **O que faz:** Lê o cache das atas e aplica o mapeamento de 12 macrocategorias do conselho através de RegEx (configuradas no `config_ambiente.py`).
  * **Cálculo de Relevância:** Mede a "intensidade" de cada assunto, calculando a proporção que o debate ocupou na reunião e aplicando "sarrafos" estatísticos (ex: ignorando temas com menos de 5% de relevância) para eliminar ruídos.
  * **Auditoria XAI:** Injeta as colunas `Palavras_Chave_Ativadas` (mostrando o gatilho exato que a IA leu, sem repetições por ata) e `Trecho_Prova_(Auditoria)` (trazendo o texto original como prova documental). Gera o Data Lake `temas_debatidos.csv`.
* **`motores/atualizar_cache_auto.py`:** Orquestrador que roda em segundo plano para manter o cérebro JSON atualizado.

### 📊 5. Interface e Geradores de Produtos (Camada Ouro)
* Módulos geradores de relatórios.
* **`analisadores/relatorio_cadeiras.py`:** Orquestrador XAI duplo. Gera o Relatório Snapshot (Matriz Histórica da máquina) e exporta a planilha Auditoria_Humana_XAI.xlsx (Camada Staging) estruturada para preenchimento ágil da equipe de auditores.
* **`analisadores/relatorio_visitantes.py`:** Consolida as frequências de visitantes, criando o "Ranking de Lobby/Ativismo" (pessoas que foram a mais de 1 reunião). Preserva o Snapshot da máquina na Fase 1.
* **`analisadores/exportador_bases_graficos.py`:** Consolida dados complexos em planilhas limpas para dashboards.
* **`analisadores/app_buscador.py` (O Mini Google do CMTT):** Interface web interativa construída com `Streamlit`, que atua como o principal portal de transparência ativa do projeto. O aplicativo é dividido em três módulos analíticos e implementa o padrão UX de "Gatekeeper" (Bloqueios de Sessão), forçando a leitura de notas metodológicas (st.session_state) antes de liberar o acesso a dados sensíveis.
    * 🔍 Aba 1 - Busca Inteligente: Utiliza um cache JSON e processamento via RegEx para realizar buscas textuais ultrarrápidas em todo o acervo histórico (PDFs e Planilhas) simultaneamente. Otimizado com formulários de submissão (ativação via Enter), permite múltiplos filtros dinâmicos (Ano e Ata), exportação em CSV e oferece links híbridos para o download direto da fonte bruta hospedada no repositório (GitHub Raw).
    * 📊 Aba 2 - Painel Temático: Módulo de visualização de dados focado em categorização de pautas. Consome os relatórios da modelagem de tópicos para gerar gráficos dinâmicos (via Plotly) de Relevância Anual, Contagem de Reuniões e Nuvens de Palavras personalizadas, permitindo filtrar e cruzar múltiplos temas ao longo do tempo.
    * 👥 Aba 3 - Frequência e Engajamento Histórico: Motor temporal de processamento de assiduidade. Calcula dinamicamente a taxa de presença de Titulares e Suplentes por segmento e por cadeira. É profundamente integrado ao Catálogo de Metadados, conseguindo cruzar os dados de presença com o histórico regimental para exibir, via tooltips (balões flutuantes), os antigos nomes de cada cadeira e o seu respectivo "Ciclo de Vida" (Ano de Criação e Extinção).
    * Visualização Responsiva: Interface adaptada para Desktop e Mobile, exibindo contextos de busca em tabelas formatadas.
    * Download Híbrido: Permite baixar o arquivo original (PDF ou Excel) clicando diretamente no nome da fonte (link dinâmico 📕/📗), além de exportar o relatório consolidado da busca em CSV. 
* **`analisadores/_arquivados/`:** Scripts geradores de gráficos analíticos com Plotly e NetworkX (Radar de Paridade, Sankey de Funil, Teia de Lobby).
* **`analisadores/relatorio_tematico.py`:** Formata e agrega o lago de dados gerado pelo motor temático, criando *Data Marts* prontos para uso em dashboards (Power BI). Extrai o denominador (total de reuniões), aplica embelezamento de palavras-chave (Thesaurus) e exporta as visões temporais (`bi_temas_evolucao_anual.csv`) e de nuvem de palavras (`bi_temas_nuvem_palavras.csv`).
* **`analisadores/relatorio_interesse_segmento.py` (O Cruzador Político):** Realiza o Join relacional avançado entre os temas de alta relevância (Camada Bronze) e a base de presença já corrigida (Camada Prata). Calcula matematicamente o índice de comparecimento histórico de cada segmento/cadeira dependendo da pauta dominante do dia (ex: *Qual o engajamento do segmento X quando se discute Tarifa?*). Exporta o `bi_indice_interesse_segmento.csv`.
---

## 🗄️ Ecossistema de Dados e Entregáveis (Medallion Architecture)

O projeto divide estritamente o que é "Meio" e o que é "Fim". Os arquivos gerados ficam prontos para Excel ou PowerBI:

* 📁 **`coletores/`:** Scripts de web scraping e automação de extração da fonte oficial da prefeitura.
* 📁 **`dados/` (O Data Lake):**
  * `base_dados/`: Os PDFs brutos e planilhas oficiais.
  * `configs/`: Regras e mapeamentos JSON gerados pelos construtores.
  * `processados/`: A fornalha de dados. Guarda os resultados brutos do motor (Camada Bronze: presenca_oficial.csv e visitantes_geral.csv), a ferramenta de auditoria manual (Auditoria_Humana_XAI.xlsx) e os dados auditados e consolidados (Camada Prata: *_conferido.csv).
* 📁 **`outputs/` (As Entregas Finais - Camada Ouro):** Guarda os produtos de alto nível formatados e prontos para leitura humana, divididos nas pastas relatorios/ (Tabelas Excel, Catálogo de Metadados) e graficos/ (Painéis interativos HTML e Imagens estáticas). Ninguém edita arquivos nesta pasta.

## 💾 Produtos de Dados Gerados (Outputs)
Ao rodar o `motor_extracao.py`, o sistema gera duas bases de dados no formato CSV na pasta `dados/processados/` (prontas para Excel ou PowerBI):

1. **`presenca_oficial.csv`:** (Bronze e Prata) Apenas conselheiros ativos no mandato da ata, com marcação binária (1 para presente, 0 para ausente). Inclui as colunas Periodo_Mandato (para facilitar gráficos temporais) e Nome_na_Ata para auditoria.
2. **`visitantes_geral.csv`:** (Bronze e Prata - One Big Table) Unificação das antigas bases de históricos e externos. Centraliza todos os não-conselheiros daquela ata em um único arquivo, classificando-os via coluna Tipo_Visitante. Puxa automaticamente o histórico completo (Mandatos anteriores, Segmentos e Órgãos) de quem já passou pelo conselho.

---

## ☁️ Arquitetura de Nuvem e Deploy

O sistema foi otimizado para rodar no **Streamlit Community Cloud** utilizando uma estratégia de **Baixo Consumo de Recursos (Lightweight Deploy)**, garantindo estabilidade e fluidez:

* **Processamento Local (ETL):** A extração pesada de dados e geração de cache ocorre na máquina do administrador. Isso evita que o servidor na nuvem estoure o limite de memória RAM (1GB) ao tentar processar 90+ PDFs simultaneamente, pois apenas consome o cache de resultados.
* **Hospedagem de Ativos (GitHub Raw):** Os arquivos PDF e Excel não são carregados na memória do servidor do app. Em vez disso, o sistema gera links diretos para o conteúdo "Raw" do GitHub, terceirizando o peso do download e evitando erros de sobrecarga. 
* **Performance:** Essa abordagem garante que o download seja processado pelos servidores do GitHub, deixando o App do CMTT livre apenas para a lógica de busca e interface, resultando em uma experiência rápida e sem travamentos ("Oh No" errors).
* **Secrets Compartimentados:** Variáveis críticas de repositório e senhas administrativas ficam no `.env` (local) e injetadas nos *Secrets* da nuvem, completamente isoladas do código público.

---

## 🏃 Como Executar o Pipeline de Dados (O Grafo de Execução)

O projeto segue um fluxo de extração estrito (DAG). Para atualizar o acervo inteiro, a ordem de execução no terminal deve ser:

```bash
# 1. Coleta de Novos Dados (Web Scraping)
python coletores/coletor_atas.py
python coletores/coletor_excel.py

# 2. Atualização dos Gabaritos e do Cérebro (Cache JSON)
python construtores/construtor_conselheiros.py
python construtores/construtor_index.py
python construtores/construtor_cache.py
python construtores/construtor_dicionario.py  # Gera o Catálogo de Metadados

# 3. Mineração NLP e Cruzamento de Dados (Fase 1: Snapshot da IA - Camada Bronze)
python motores/motor_extracao.py
python motores/motor_tematico.py
python analisadores/relatorio_cadeiras.py     # Gera a matriz base e a planilha de auditoria
python analisadores/relatorio_visitantes.py   # Gera o ranking inicial do lobby

# 4. Human-in-the-Loop (A Auditoria)
# -> O usuário humano abre "dados/processados/Auditoria_Humana_XAI.xlsx", preenche P ou V e salva.

# 5. Consolidação (Fase 2: Camadas Prata e Ouro)
python motores/atualizador_bases.py           # Lê as correções e gera os CSVs conferidos
# Após as bases conferidas, os relatórios finais (PowerBI/Excel) podem ser gerados.
python analisadores/exportador_bases_graficos.py
```

Para abrir o portal de buscas localmente:
```bash
streamlit run analisadores/app_buscador.py
```
*(Dica: No Windows, você pode usar o arquivo `rotina_cmtt.bat` para automatizar a atualização do cache do buscador em segundo plano via Agendador de Tarefas).*