# Etapa 1: Limpeza, Filtragem e Cruzamento de Dados (`src/limpeza`)

Este diretório concentra os módulos responsáveis pelo tratamento, higienização, cruzamento relacional (`Inner Join`) e exportação da base unificada do **Novo CAGED** com os dados demográficos dos **Municípios de Santa Catarina (IBGE)**.

---

## 1. Arquitetura em Módulos (Separação por Responsabilidades)

O código foi dividido em arquivos independentes e explícitos para facilitar a leitura e manutenção por toda a equipe:

| Arquivo | Responsabilidade Principal |
| :--- | :--- |
| [`limpeza_municipios.py`](./limpeza_municipios.py) | Carrega `Municipios_SC_limpo.csv`, padroniza cabeçalhos sujos, descarta colunas irrelevantes e gera a chave municipal de 6 dígitos (`codigo_municipio_6d`). |
| [`limpeza_caged.py`](./limpeza_caged.py) | Carrega `Novo_Caged_MOV_Limpo.csv`, remove colunas de índice sobressalentes, filtra o recorte industrial (**Seções B a F**) e converte campos monetários/decimais (`salário`, `valorsaláriofixo`, `horascontratuais`) de texto com vírgula para `float`. |
| [`cruzamento_dados.py`](./cruzamento_dados.py) | Realiza o cruzamento relacional (`Inner Join`) entre as movimentações do CAGED e os indicadores municipais do IBGE utilizando o código de 6 dígitos. |
| [`exportacao_dados.py`](./exportacao_dados.py) | Exporta a tabela limpa e unificada para o arquivo `database/doc/Caged_Industrial_SC_Limpo_Unificado.csv`, permitindo que as análises seguintes não precisem reprocessar o arquivo bruto de 3,4 milhões de linhas. |
| [`pipeline_limpeza.py`](./pipeline_limpeza.py) | Orquestrador que executa sequencialmente as 4 etapas acima e exibe o relatório de validação no terminal. |

---

## 2. Decisões Técnicas e de Negócio Adotadas

### 2.1. Recorte do Setor Industrial: Por que filtrar as Seções `B` até `F`?
O desafio central do Datathon foca no **setor industrial catarinense** (*"Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada..."*).
A base original do Novo CAGED possui **3.397.416 registros** distribuídos em todas as atividades da economia (de `A` a `U`, incluindo comércio varejista, administração pública, serviços domésticos, etc.).

Seguindo a classificação oficial do **IBGE, CNI (Confederação Nacional da Indústria) e FIESC**, filtramos o **Setor Industrial Completo**, composto pelas seções:
* **`B` — Indústrias Extrativas:** Mineração de carvão, extração de minerais não-metálicos, etc.
* **`C` — Indústrias de Transformação:** O núcleo fabril do estado (Têxtil, Confecção, Metalmecânica, Máquinas, Plásticos, Móveis, Eletroeletrônica e Alimentos).
* **`D` e `E` — Serviços Industriais de Utilidade Pública (SIUP):** Eletricidade, gás, água, saneamento e gestão de resíduos industriais.
* **`F` — Construção:** Indústria da construção civil e infraestrutura.

> **Por que a Seção `A` (Agropecuária) não entrou e onde está a Agroindústria?**
> Na tabela CNAE (`subclasse`), a **Seção `A`** refere-se exclusivamente à atividade primária no campo (plantio de lavouras e criação de animais no pasto). Já a **Agroindústria catarinense** (frigoríficos de abate de aves, suínos e bovinos, laticínios, processamento de carnes, madeira e papel/celulose — divisões 10, 11, 16 e 17 do CNAE) **já está integralmente contida dentro da Seção `C` (Indústria de Transformação)**. Assim, isolar a Seção `A` evita distorcer a análise industrial com a sazonalidade da colheita agrícola, mantendo 100% da agroindústria fabril do Oeste e da Serra na nossa base.

Com esse filtro, a base passa de `3.397.416` para **`1.141.403` movimentações industriais**.

---

### 2.2. Padronização da Chave Municipal para o `Inner Join` (7 dígitos vs. 6 dígitos)
Ao inspecionar as duas bases, identificamos uma divergência estrutural nos códigos dos municípios:
* Na base do **IBGE** (`Municipios_SC_limpo.csv`), o código do município possui **7 dígitos** (ex: Jaraguá do Sul = `4208906`), onde o último algarismo (`6`) é o dígito verificador.
* Na base do **Novo CAGED** (`Novo_Caged_MOV_Limpo.csv`), a coluna `município` armazena apenas os **6 primeiros dígitos** (ex: Jaraguá do Sul = `420890`), omitindo o dígito verificador.

**Solução:**
1. O rodapé HTML residual ao final do arquivo `Municipios_SC_limpo.csv` foi removido para manter exatamente os **295 municípios** de Santa Catarina.
2. No módulo [`limpeza_municipios.py`](./limpeza_municipios.py), extraímos os 6 primeiros dígitos do código IBGE para a coluna `codigo_municipio_6d`.
3. O `Inner Join` entre `município` (CAGED) e `codigo_municipio_6d` (IBGE) atingiu **100% de correspondência** (`1.141.403` registros cruzados sem perda de linhas).

---

### 2.3. Limpeza dos Cabeçalhos e Colunas de Municípios
Os nomes originais das colunas em `Municipios_SC_limpo.csv` continham sufixos como `[-]`, `[2025]`, tags HTML (`<span>6 a 14 anos</span>`) e uma coluna vazia ao final gerada por vírgula sobressalente (`Unnamed: 14`).
* Todas as colunas foram renomeadas explicitamente para identificadores limpos em `snake_case` (ex: `nome_municipio`, `populacao_estimada_2026`, `pib_per_capita_2023`, `idhm_2010`).
* Colunas sem relação com o problema de negócio (como `prefeito`, `gentilico`, `mortalidade_infantil`, `receitas_brutas` e `despesas_brutas`) e as colunas de índice do CAGED (`Unnamed: 0.1` e `Unnamed: 0`) foram descartadas para reduzir o consumo de memória e deixar a base visualmente limpa.

---

### 2.4. Tratamento de Variáveis Numéricas (`salário`)
No arquivo original do CAGED, os valores monetários e de carga horária estavam formatados no padrão textual brasileiro com vírgula decimal (ex: `"2018,00"`).
* Aplicamos a substituição explícita de `","` por `"."` e a conversão para ponto flutuante (`float`), viabilizando cálculos estatísticos de média salarial, mediana e desvio padrão.

---

## 3. Como Executar a Pipeline de Limpeza

A partir da raiz do projeto, execute:

```bash
python src/limpeza/pipeline_limpeza.py
```

O script irá processar os dados e salvar automaticamente a base pronta para análise em:
`database/doc/Caged_Industrial_SC_Limpo_Unificado.csv`
