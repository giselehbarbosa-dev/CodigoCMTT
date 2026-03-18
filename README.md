🏛️ Projeto CMTT - Mineração e Análise de Dados (Fase 1)
Documentação Oficial da Arquitetura de Extração de Identidades

O CMTT Pipeline evoluiu para um modelo de Explainable AI (XAI). Em vez de uma caixa-preta de decisões, o sistema adota a estratégia de Alta Revogação (High Recall): ele busca todas as combinações possíveis de nomes para evitar perdas (falsos negativos), mas 'confessa' o que leu em uma coluna de auditoria, permitindo uma validação humana rápida e 100% segura.

🎯 Objetivo da Fase 1
Criar um pipeline automatizado e escalável capaz de ler atas em PDF do Conselho Municipal de Trânsito e Transporte (CMTT), extrair os nomes dos presentes, cruzar com a base oficial de conselheiros (titulares e suplentes) e classificar os participantes entre Oficiais, Históricos e Visitantes Externos, lidando com erros de digitação, lixo de chat e extração de texto sujo.
Além disso, disponibilizar uma interface de busca flexível (App Web) para consulta rápida em todo o acervo histórico.

## ⚙️ Pré-requisitos e Instalação (Setup)
Para garantir a reprodutibilidade do projeto em qualquer máquina, é necessário instalar as bibliotecas base e o modelo de linguagem do spaCy.

**1. Instale as bibliotecas via terminal:**
`pip install pandas numpy pdfplumber thefuzz spacy streamlit tqdm`

**2. Faça o download do modelo gramatical do spaCy (em português):**
`python -m spacy download pt_core_news_sm`

## 🏗️ Arquitetura do Sistema (Módulos)
O projeto foi desenhado sob o princípio de Separação de Responsabilidades (Separation of Concerns). Cada arquivo tem uma função única e específica, permitindo que o código seja facilmente adaptado para outros conselhos ou cidades no futuro.

### 📁 Pasta: `extratores/` (A Fábrica de Dados)

* **1. `config_filtros.py` (O "Enfermeiro")**
  * Módulo focado exclusivamente no tratamento básico e "cego" de strings.
  * **O que faz:** Remove acentos, esmaga espaços duplos, limpa caracteres especiais e faz a conversão de strings de período (ex: "2013ago") para objetos datetime do Python.
  * **Escalabilidade:** 100% universal para qualquer texto em português.

* **2. `gerenciador_io.py` (O "Bibliotecário")**
  * Responsável pelas entradas e saídas (Input/Output) do sistema.
  * **O que faz:** Abre os PDFs usando `pdfplumber`, extrai o texto bruto removendo quebras de linha invisíveis do Windows, carrega os JSONs de configuração e valida a existência das pastas.

* **3. `construtor_index.py` (O "Indexador")**
  * Mapeia o caos de arquivos e planilhas soltas.
  * **O que faz:** Lê a planilha de controle de atas, usa Expressões Regulares (RegEx) flexíveis para ignorar cabeçalhos, extrair datas/locais e criar um dicionário de gabarito (`index_atas.json`) vinculando cada PDF ao seu respectivo mandato e reunião.

* **4. `construtor_conselheiros.py` (O "RH")**
  * Mapeia a estrutura de poder do Conselho.
  * **O que faz:** Lê a planilha oficial de mandatos do Excel, entende quem tem direito a voto, agrupa titulares e suplentes por segmento/cadeira (usando chaves compostas) e gera JSONs determinísticos e padronizados para cada mandato. Possui blindagem contra cabeçalhos mal digitados e células vazias (NaN). Possui trava de Auditoria de Vacância (assinala cadeiras sem nome como "VAGO" em vez de excluí-las).

* **5. `ferramentas_matcher.py` (O "Cirurgião com Inteligência Artificial")**
  * O verdadeiro cérebro da operação de cruzamento de dados.
  * **O que faz:**
    * Usa a IA do `spaCy` para análise morfossintática, eliminando verbos, pronomes e advérbios soltos.
    * Usa a matemática de proximidade (`thefuzz`) para tolerar erros de digitação nos nomes.
    * Possui o "Exterminador em Loop" para decapitar preposições e títulos (Sr., Dra., Conselheira).
    * Usa Extração Inversa por Prefixos para barrar centenas de termos institucionais e lixos de chat sem bloquear nomes próprios.
    * Resolve a ambiguidade de nomes curtos (ex: "Rafael"), vasculhando os arquivos e criando a coluna `Nome_Associado` para diferenciar Conselheiros de Munícipes comuns.
    * Lógica Invertida (Anti-Fantasmas): Exige que múltiplas partes do nome oficial sejam encontradas na ata para validar a presença, erradicando falsos positivos.
    * **Nova Lógica de Arrastão (N-Grams):** Agora utiliza a biblioteca itertools para gerar combinações automáticas de nomes (ex: Primeiro + Último). Isso garante que o sistema capture variações como "Ana de Paula" ou "Rita Paula", mesmo que o nome oficial seja "Ana Rita de Paula".

Sistema de Confissão: A função de busca foi alterada para retornar não apenas o "match", mas o trecho bruto lido no PDF, alimentando a nova coluna de auditoria.

* **6. `motor_extracao.py` (O "Maestro")**
  * O arquivo principal que orquestra todos os outros.
  * Barra de Progresso: Implementação da tqdm para monitoramento visual do tempo de processamento das atas.
  * Auditoria XAI: Agora injeta a coluna Nome_na_Ata no CSV oficial, permitindo conferência humana instantânea de falsos positivos.
  * **O que faz:** Roda o loop principal pelas atas, aplica táticas "Anti-Negrito" e "Anti-Anexos" na leitura, chama o matcher para separar as entidades e exporta o resultado, ordenando perfeitamente a lista alfabética e ignorando acentos. Aplica o **Bypass Ninja**: Lê o texto bruto linha a linha para curar a "cegueira" da IA em tabelas espremidas do PDF, garantindo a captura de 100% dos conselheiros presentes.

### 📁 Pasta: `analisadores/` (Interface e Relatórios)

* **`relatorio_cadeiras.py`:** Gera a linha do tempo (Matriz) de presença, calcula a Taxa de Absenteísmo (%) e o Ranking de Rotatividade por cadeira.
* **`relatorio_visitantes.py`:** Consolida as frequências de visitantes externos e históricos, criando o "Ranking de Lobby/Ativismo" (pessoas que foram a mais de 1 reunião).
* **`app_buscador.py` (O Mini Google do CMTT):** Interface web interativa construída com `Streamlit`.
    * **Busca Inteligente:** Utiliza um cache JSON e processamento via RegEx para realizar buscas ultra-rápidas em todo o acervo histórico (PDFs e Planilhas) simultaneamente.
    * **Visualização Responsiva:** Interface adaptada para Desktop e Mobile, exibindo contextos de busca em tabelas formatadas.
    * **Download Híbrido:** Permite baixar o arquivo original (PDF ou Excel) clicando diretamente no nome da fonte (link dinâmico 📕/📗), além de exportar o relatório consolidado da busca em CSV. 

---

## ☁️ Arquitetura de Nuvem e Deploy

O sistema foi otimizado para rodar no **Streamlit Community Cloud** utilizando uma estratégia de **Baixo Consumo de Recursos (Lightweight Deploy)**:

* **Processamento Local (ETL):** A extração pesada de dados e geração de cache ocorre na máquina do administrador. Isso evita que o servidor na nuvem estoure o limite de memória RAM (1GB) ao tentar processar 90+ PDFs simultaneamente.
* **Hospedagem de Ativos (GitHub Raw):** Os arquivos PDF e Excel não são carregados na memória do servidor do app. Em vez disso, o sistema gera links diretos para o conteúdo "Raw" do GitHub. 
* **Performance:** Essa abordagem garante que o download seja processado pelos servidores do GitHub, deixando o App do CMTT livre apenas para a lógica de busca e interface, resultando em uma experiência rápida e sem travamentos ("Oh No" errors).

---

## 💾 Produtos de Dados Gerados (Outputs)
Ao rodar o `motor_extracao.py`, o sistema gera três bases de dados no formato CSV na pasta `dados/processados/` (prontas para Excel ou PowerBI):

1. **`presenca_oficial.csv`:** Apenas conselheiros ativos no mandato da ata, com marcação binária (1 para presente, 0 para ausente). Inclui as colunas Periodo_Mandato (para facilitar gráficos temporais) e Nome_na_Ata para auditoria.
2. **`visitantes_geral.csv`:** (One Big Table) - Unificação das antigas bases de históricos e externos. Centraliza todos os não-conselheiros daquela ata em um único arquivo, classificando-os via coluna Tipo_Visitante. Puxa automaticamente o histórico completo (Mandatos anteriores, Segmentos e Órgãos) de quem já passou pelo conselho.
---

## 🏃 Como Executar o Projeto

**Para extrair os dados e gerar os CSVs Oficiais:**
Rode os ficheiros na seguinte ordem no seu terminal:
```bash
python extratores/construtor_conselheiros.py
python extratores/construtor_index.py
python extratores/motor_extracao.py

Para gerar os relatórios Excel de Presença e Lobby:

Bash
python analisadores/relatorio_cadeiras.py
python analisadores/relatorio_visitantes.py
Para abrir a Interface de Busca Rápida (App Web):

Bash
streamlit run analisadores/app_buscador.py
(Dica: Pode também usar o ficheiro rotina_cmtt.bat para automatizar a atualização do cache do buscador em segundo plano com um duplo clique).