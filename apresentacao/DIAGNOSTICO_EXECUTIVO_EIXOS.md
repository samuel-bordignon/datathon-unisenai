# Relatório Diagnóstico Integrado: Raio-X do Mercado de Trabalho Industrial de SC
## Resposta à Pergunta Central de Negócio e Análise Comparativa dos 3 Eixos
**Projeto:** Datathon 2026 — Semana Acadêmica de Ciência de Dados e Inteligência Artificial  
**Público-Alvo:** FIESC, Secretarias de Desenvolvimento Econômico e Banca Avaliadora  
**Base de Dados:** Microdados do Novo CAGED (12 meses: Setembro/2025 a Agosto/2026) unificados com Censo/Estimativas IBGE 2026  
**Total de Movimentações Industriais Auditadas:** **1.139.633 vínculos** (571.139 admissões e 568.494 desligamentos | Saldo Líquido: **+2.645**)

---

## 1. Resposta Direta e Conclusiva à Pergunta Central de Negócio

> **Pergunta Central:**  
> *“Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?”*

### Síntese do Diagnóstico Executivo:

1. **Onde está a Expansão Acelerada?**
   - **Regiões:** **Foz do Rio Itajaí (Navegantes)** lidera em atratividade e densidade de novos postos (+2.765 de saldo líquido; **280,9 vagas/10 mil habitantes**), seguida pelo polo metalmecânico do **Norte (Joinville)** (+1.527 saldo) e pela agroindústria do **Oeste (Chapecó com +1.110 e Guatambú com +595 e pico de 598,2 vagas/10k hab)**.
   - **Setores:** A **Fabricação de Produtos Alimentícios** lidera a expansão com saldo de **+4.739 postos** (90,8 mil admissões), seguida pela **Fabricação de Máquinas, Aparelhos e Materiais Elétricos** (+2.018) e **Serviços Especializados para Construção Civil** (+1.892).

2. **Onde está o Apagão de Mão de Obra e a Retração?**
   - **Retração Estrutural:** O tradicional polo têxtil do **Vale do Itajaí** enfrenta encolhimento acentuado (**Blumenau com saldo de -842 e Gaspar com -535**), reflexo da crise de competitividade da **Confecção de Roupas (-4.571 vagas)** e **Têxtil (-793)**. Na Grande Florianópolis, **São José** amarga o pior saldo estadual (**-990 vagas**).
   - **O Verdadeiro "Apagão" (Gargalo de Retenção):** Não se trata de desemprego alto ou falta de candidatos gerais em SC, mas de uma **crise severa de retenção na base operacional**. Em setores como Alimentos e Bebidas, **62,1%** de todas as rescisões ocorrem por **Pedido de Demissão espontâneo do trabalhador (Código 40)** (atingindo **74,9% em Concórdia**). Em Joinville, no setor elétrico, a taxa de pedidos espontâneos chega a **60,0%**.

3. **Como a Renda e a Escolaridade Explicam esses Gargalos?**
   - **O Mecanismo da Renda (A Armadilha do Piso Salarial):** O trabalhador que pede demissão recebe salário mediano de **R$ 2.241,80**, praticamente estagnado no salário inicial de admissão (**R$ 2.209,85**). A ausência de perspectivas de crescimento e a concorrência com o setor terciário (comércio, logística portuária e serviços) em cidades dinâmicas faz com que o operário abandone a indústria.
   - **A Compressão Salarial (Código 31 - Demissões pela Empresa):** As empresas desligam os profissionais de maior escolaridade e experiência (média de **R$ 2.962,35**, mediana de **R$ 2.556,00**, com 5,8% de nível superior) e contratam novatos com salário médio de **R$ 2.478,48** (mediana **R$ 2.209,85**, 4,2% superior). Trata-se de uma troca precarizante com **deságio médio de -16,3% (-R$ 483,87 por vaga)**, o que agrava a rotatividade e corrói a memória técnica fabril.
   - **O Nível de Escolaridade:** Mais de **60% da força industrial** possui Ensino Médio Completo. O gargalo do apagão **não está na falta de engenheiros ou pós-graduados**, mas na **baixa atratividade financeira dos cargos operacionais de base** frente ao custo de vida das regiões em expansão.

---

## 2. Análise Comparativa dos Três Eixos do Hackathon

| Dimensão de Análise | Eixo 1: Territorial e Setorial | Eixo 2: Perfil Socioeconômico | Eixo 3: Qualificação e IA (CBOs) |
| :--- | :--- | :--- | :--- |
| **Pergunta Norteadora do Guia** | *Como as movimentações estão distribuídas? Quais municípios e setores concentram saldos positivos ou encolhem?* | *Qual o perfil de admitidos vs desligados? Há contratação de instruídos ou compressão salarial?* | *Os cargos em escassez exigem nível técnico/engenharia ou base operacional? Como a IA revela os padrões?* |
| **Variáveis-Chave Analisadas** | Município, Região Imediata, Seção CNAE, Divisão CNAE, Saldo por 10k hab. | Tipo de Movimentação (Cód. 40, 31, 43/45), Salário Nominal, Escolaridade. | Famílias CBO2002, 19 Macrofamílias geradas por IA, Grau de Instrução Predominante. |
| **Principal Descoberta** | **Bipolaridade Econômica:** Expansão acelerada no litoral norte/portuário e no agro-oeste vs. sangria no Vale Têxtil e Grande Fpolis. | **O Paradigma do Cód. 40:** 47,7% das saídas são por iniciativa do próprio trabalhador devido à estagnação salarial na base (R$ 2.241). | **Gargalo é Chão de Fábrica:** 82% das movimentações e 94% dos pedidos de demissão estão em Operação e Apoio Industrial. |
| **Métrica Crítica** | Navegantes (+280,9 saldo/10k hab) vs. Blumenau (-21,6 saldo/10k hab). | Troca de custo Cód. 31 (R$ 2.962) por Admissão (R$ 2.478): -16,3% de deságio. | Alimentos e Bebidas tem 62,1% de pedidos de demissão voluntária com piso R$ 2.169. |
| **Implicação Estratégica** | Políticas de atração e infraestrutura urbana regionalizadas. | Revisão urgente dos planos de progressão e carreiras de chão de fábrica. | Treinamentos técnicos "on-the-job" com certificação modular vinculada a faixas salariais. |

---

## 3. Detalhamento dos Resultados por Eixo

### EIXO 1: Territorial e Setorial

#### 1. Top 5 Polos de Expansão Acelerada
1. **Navegantes:** Saldo de **+2.765** vagas (11.819 admissões vs 9.054 desligamentos). Saldo por 10 mil habitantes: **280,9**. Salário médio de R$ 2.632,56. Alavancado pelo Porto de Navegantes, indústria da pesca e estaleiros navais.
2. **Joinville:** Saldo de **+1.527** vagas (50.041 admissões vs 48.514 desligamentos). Saldo por 10 mil habitantes: **22,7**. Salário médio: R$ 2.765,29. Líder absoluto em volume manufatureiro metalmecânico e elétrico.
3. **Chapecó:** Saldo de **+1.110** vagas (25.058 admissões vs 23.948 desligamentos). Saldo por 10 mil habitantes: **38,4**. Salário médio: R$ 2.567,32. Capital da agroindústria e proteína animal.
4. **Guatambú:** Saldo de **+595** vagas (3.431 admissões vs 2.836 desligamentos). Saldo por 10 mil habitantes: **598,2** (a mais alta densidade de expansão de SC). Polo satélite frigorífico com grande pressão demográfica.
5. **Canoinhas:** Saldo de **+573** vagas (2.867 admissões vs 2.294 desligamentos). Saldo por 10 mil habitantes: **100,2**. Crescimento expressivo na cadeia de madeira/celulose.

#### 2. Top 5 Polos em Retração Industrial
1. **São José:** Saldo de **-990** vagas (9.632 admissões vs 10.622 desligamentos). 49,9% dos desligamentos realizados pela empresa (Cód. 31). Transição de área fabril para serviços na Região Metropolitana de Florianópolis.
2. **Blumenau:** Saldo de **-842** vagas (31.030 admissões vs 31.872 desligamentos). Desaceleração acentuada do polo têxtil tradicional com alta evasão voluntária de operários (47,8% Cód. 40).
3. **Gaspar:** Saldo de **-535** vagas (9.281 admissões vs 9.816 desligamentos). Reflexo direto da retração da cadeia de confecção de roupas do Vale.
4. **Criciúma:** Saldo de **-496** vagas (13.306 admissões vs 13.802 desligamentos). Encolhimento na indústria cerâmica e vestuário.
5. **Araranguá:** Saldo de **-461** vagas (3.095 admissões vs 3.556 desligamentos).

#### 3. Top Setores em Expansão vs. Retração (CNAE Divisão)
* **Fabricação de Produtos Alimentícios (CNAE 10):** Saldo de **+4.739** postos (90.790 admissões vs 86.051 saídas). Salário médio: R$ 2.259,90.
* **Máquinas e Materiais Elétricos (CNAE 27):** Saldo de **+2.018** postos (17.509 admissões vs 15.491 saídas). Salário médio: R$ 2.615,80.
* **Serviços de Construção (CNAE 43):** Saldo de **+1.892** postos. Salário médio: R$ 2.650,05.
* **Confecção de Artigos do Vestuário (CNAE 14):** Saldo de **-4.571** postos (57.494 admissões vs 62.065 saídas). Salário médio: R$ 2.343,54.
* **Fabricação de Produtos de Madeira (CNAE 16):** Saldo de **-1.391** postos. Salário médio: R$ 2.194,66.
* **Fabricação de Móveis (CNAE 31):** Saldo de **-1.319** postos. Salário médio: R$ 2.397,43.

---

### EIXO 2: Perfil Socioeconômico e Dinâmica de Movimentação

A literatura tradicional de recursos humanos frequentemente assume que altas taxas de desligamento refletem "demissões por falta de produtividade". Os microdados do Novo CAGED de Santa Catarina revelam o oposto:

```
Total de Desligamentos em SC: 568.494 trabalhadores
├── Código 40 (Pedido de Demissão pelo Trabalhador): 271.098 (47,7%)  <-- GARGALO DE RETENÇÃO
├── Código 31 (Demissão sem Justa Causa pela Empresa): 191.306 (33,6%) <-- COMPRESSÃO SALARIAL
├── Códigos 43/45 (Fim de Contrato / Experiência):      81.970 (14,4%)  <-- TURNOVER TEMPORÁRIO
└── Outros Motivos (Acordos, Falecimentos, Transfer.):   24.120  (4,2%)
```

#### Comparativo de Rendimentos por Grupo de Movimentação:
- **Admitidos (+1):** Média R$ 2.478,48 | Mediana R$ 2.209,85 | Nível Superior: 4,24%
- **Pedido de Demissão (Cód 40):** Média R$ 2.523,06 | Mediana R$ 2.241,80 | Nível Superior: 4,88%
- **Demissão pela Empresa (Cód 31):** Média R$ 2.962,35 | Mediana R$ 2.556,00 | Nível Superior: 5,80%
- **Término de Contrato (Cód 43/45):** Média R$ 2.237,10 | Mediana R$ 2.142,39 | Nível Superior: 2,20%

#### As Duas Evidências Científicas Incontestáveis:
1. **O Colapso da Retenção no Chão de Fábrica:** O funcionário que pede para sair ganha apenas R$ 32,00 a mais por mês (em mediana) do que quando entrou. Como o custo de moradia e alimentação subiu no estado e o setor de logística/comércio oferece vagas imediatas, o trabalhador pede demissão em massa.
2. **A "Economia da Troca" Precarizante:** As indústrias estão ativamente desligando funcionários com salários mais elevados (R$ 2.962) para recontratar com pisos mais baixos (R$ 2.478). Essa estratégia gera uma falsa economia de curto prazo de 16,3% na folha, mas agrava o apagão operacional pelo custo invisível de integração e retrabalho.

---

### EIXO 3: Qualificação e Macrofamílias de CBOs com IA

Com apoio de Inteligência Artificial e regras determinísticas baseadas no Catálogo Oficial do MTE e Dicionário do CAGED, mais de 2.000 CBOs foram sintetizados em 19 macrofamílias analíticas:

#### Desempenho das Principais Macrofamílias:
1. **Produção e Apoio Industrial:** 319.154 movimentações (28,0% do total de SC). Saldo positivo de **+9.622 vagas**. Salário médio de R$ 2.304,78. Taxa de Pedidos de Demissão voluntária: **52,8%**.
2. **Construção e Infraestrutura:** 191.234 movimentações. Saldo de **+1.324 vagas**. Salário médio de R$ 2.705,75. Taxa de Pedidos Cód. 40: 39,3%.
3. **Têxtil, Vestuário e Couro:** 108.224 movimentações. Saldo negativo de **-3.446 vagas**. Salário médio de R$ 2.287,13. Taxa de Pedidos Cód. 40: **55,3%**.
4. **Alimentos e Bebidas:** 48.719 movimentações. Saldo positivo de **+2.925 vagas**. Salário médio de R$ 2.169,58. Taxa de Pedidos Cód. 40: **62,1%** (o maior índice de evasão do estado).
5. **Engenharia, Pesquisa e Projetos:** 9.701 movimentações. Saldo de **-763 vagas**. Salário médio de R$ 4.964,82. Taxa de Pedidos Cód. 40: 45,5%.
6. **Gestão e Direção:** 17.719 movimentações. Saldo de **-3.709 vagas**. Salário médio de R$ 6.250,11. Taxa de Pedidos Cód. 40: 32,8%.

#### A Matriz dos Polos Críticos Prioritários:
Cruzando Município × Setor CNAE × Macrofamília CBO, localizamos os epicentros do problema:
* **Joinville / Fabricação de Máquinas Elétricas / Elétrica e Automação:** 6.946 movimentações; **60,0%** das saídas por iniciativa do trabalhador; salário mediano 3,1% abaixo da referência estadual.
* **Concórdia / Alimentos / Alimentos e Bebidas:** 4.220 movimentações; **74,9%** dos desligamentos são voluntários a pedido do trabalhador; remuneração mediana 10,9% abaixo do padrão de mercado.
* **Blumenau / Vestuário / Têxtil e Confecção:** 5.550 movimentações; **56,0%** saídas a pedido; salário mediano 6,5% abaixo da referência.
* **Videira / Alimentos / Alimentos e Bebidas:** 2.872 movimentações; **71,6%** saídas voluntárias.

---

## 4. Recomendações Acionáveis para a Indústria e Entidades de Classe

1. **Instituição do Plano de Progressão Operacional (FIESC / Sindicatos Patronais):**
   - Criar patamares salariais claros nos primeiros 6, 12 e 24 meses de empresa para cargos operacionais de entrada. A estagnação no piso (R$ 2.241) é o gatilho direto dos 47,7% de pedidos de demissão.
2. **Trilhas de Formação Rápida "In-Company" (SENAI/SESI):**
   - Implementar microcertificações industriais focadas nas carências de base (alimentadores de linha, montadores industriais e técnicos em automação) com incentivos de bolsa e elevação salarial imediata após a conclusão.
3. **Plano de Atração e Retenção nos Polos Portuários e Agroindustriais:**
   - Em Navegantes e no Grande Oeste, a indústria deve articular parcerias com prefeituras para subsídio de transporte integrado, habitação de interesse social e benefícios indiretos (creches de turno e convênios), mitigando a perda de operários para cidades vizinhas ou outros setores econômicos.
