# Análises dos Três Eixos e Validação das Hipóteses (`src/analises/`)

Este diretório contém a pipeline analítica refatorada que consome a base limpa e unificada (`database/doc/Caged_Industrial_SC_Limpo_Unificado.csv`) e responde com evidências numéricas à **Pergunta Central de Negócio** do Guia do Participante:

> *“Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?”*

---

## 1. Como Executar

Na raiz do repositório:

```bash
# 1. Executar todos os testes unitários
python -m unittest discover -s src/analises -p "test_*.py" -v

# 2. Executar a pipeline integrada dos 3 Eixos (ou cada eixo individualmente)
python src/analises/executar_analises.py
```

Os resultados (tabelas CSV com separador `;`, gráficos PNG, auditoria e relatório em Markdown) são exportados automaticamente em `database/resultados/`.

---

## 2. O Que Refatoramos e Por Que o `tipomovimentação` (`Cód. 40`, `31` e `43/45`) Mudou o Jogo

Na versão inicial da análise, todas as saídas de trabalhadores (`saldomovimentação == -1`) eram agrupadas em um único bloco chamado **`Desligamento`**.
Porém, ao separar a coluna `tipomovimentação` segundo o Dicionário Oficial do CAGED, descobrimos que misturar todos os desligamentos escondia dois fenômenos opostos:

| Grupo de Movimentação | Código CAGED | Volume (Set/25–Ago/26) | % das Saídas | O que significa no mundo real da Indústria? |
| :--- | :---: | ---: | ---: | :--- |
| **1. Admitidos (`+1`)** | `10, 20, 25, 35, 70, 97` | **571.139** | — | Contratações formais realizadas pela indústria. |
| **2. Pedido de Demissão (Trabalhador saiu)** | **`40`** | **271.098** | **47,7%** | **Sinal de Baixa Retenção / Desatratividade:** A empresa precisava do funcionário, mas ele pediu as contas voluntariamente. |
| **3. Demissão sem Justa Causa (Empresa demitiu)** | **`31`** | **191.306** | **33,7%** | **Sinal de Substituição ou Corte:** A empresa decidiu desligar o funcionário (por custo, reestruturação ou inadequação técnica). |
| **4. Fim de Contrato Temporário** | **`43 e 45`** | **81.970** | **14,4%** | **Giro Sazonal Previsto:** Contratos de prazo determinado/experiência cujo encerramento já era esperado desde a contratação. |
| **5. Outros Desligamentos** | `32, 33, 50, 60, 80, 90, 98` | **24.120** | **4,2%** | Justa causa, acordo, aposentadoria, transferência ou óbito. |

---

## 3. Confronto com o Documento Origem: O Que Conseguimos Provar?

Abaixo está a validação de cada um dos **3 Eixos do Guia do Participante**, mostrando a hipótese, os dados reais extraídos e a conclusão para o **Storytelling e Pitch Executivo**.

---

### EIXO 1: Territorial e Setorial — *Expansão Acelerada vs. Apagão e Retração*

#### Hipótese testada:
*Existem municípios e setores concentrando o crescimento acelerado (pressionando a população local), enquanto outros sofrem com altíssima rotatividade ou encolhimento?*

#### O que os dados provaram (`database/resultados/eixo1_territorial/`):

1. **Polos de Expansão Acelerada (`Saldo por 10.000 habitantes`):**
   * **Navegantes** lidera tanto no saldo absoluto (**`+2.742` vagas**) quanto na expansão proporcional entre cidades médias/grandes (**`+278,6` vagas por 10 mil hab**), impulsionada pela construção civil, logística e indústria naval/metalmecânica.
   * **Joinville** (`+1.663` vagas | `+24,7/10k hab`) e **Chapecó** (`+1.091` vagas | `+37,7/10k hab`) lideram o volume bruto nos polos Norte e Oeste.
   * Cidades industriais menores próximas a grandes polos sofrem **pressão demográfica extrema**, como **Guatambú** (colada em Chapecó, com **`+596,2` vagas por 10 mil hab**), **Agrolândia** (`+170,4/10k hab`), **Otacílio Costa** (`+159,8/10k hab`) e **São Ludgero** (`+155,5/10k hab`). Nessas cidades, o crescimento de vagas supera a capacidade populacional local, exigindo atração de trabalhadores de municípios vizinhos.

2. **Setores Locomotivas vs. Setores em Retração (Divisões CNAE):**
   * **Quem mais cresce:**
     * **Fabricação de Produtos Alimentícios (CNAE 10 — Agroindústria):** Maior saldo líquido do estado (**`+4.368` vagas**, com `91.471` admissões e `87.103` desligamentos).
     * **Fabricação de Máquinas e Equipamentos (CNAE 28):** Saldo de **`+1.797` vagas** e salário médio elevado (`R$ 3.310,16`).
     * **Fabricação de Produtos de Metal (CNAE 25):** Saldo de **`+1.477` vagas** (`R$ 2.866,01`).
     * **Materiais Elétricos e Eletrônicos (CNAE 27 e 26):** Saldo somado de **`+1.652` vagas** e a menor taxa de rotatividade da indústria catarinense.
   * **Quem mais encolhe:**
     * **Confecção de Artigos do Vestuário (CNAE 14) e Têxtil (CNAE 13):** Perda líquida combinada de **`-4.882` vagas** (mais o setor de **Couro e Calçados CNAE 15** com **`-972` vagas**, totalizando **`-5.854` vagas** na cadeia têxtil/vestuário/calçados).
     * **Madeira (CNAE 16) e Móveis (CNAE 31):** Perda combinada de **`-2.163` vagas**.
     * **Municípios impactados pela retração setorial:** **São José** (`-985`), **Blumenau** (`-832`), **Gaspar** (`-502`), **Criciúma** (`-495`) e **Araranguá** (`-464`).

---

### EIXO 2: Perfil Socioeconômico — *Como Renda e Escolaridade Explicam os Gargalos?*

#### Hipótese testada:
*A dificuldade de reter trabalhadores (apagão) decorre de salários pouco atrativos, e as empresas estão trocando trabalhadores mais caros por contratações mais baratas?*

#### O que os dados provaram (`database/resultados/eixo2_socioeconomico/`):

Compare o resultado **Sem separar o Tipo de Movimentação** (visão tradicional) contra a **Visão por Motivo de Movimentação (`Códigos 40, 31 e 43/45`)**:

| Grupo Analisado | Movimentações | Salário Médio (R\$) | Mediana Salarial (R\$) | % com Ensino Superior Completo |
| :--- | ---: | ---: | ---: | ---: |
| **Visão Tradicional: Admitidos Geral** | 571.139 | R\$ 2.478,48 | R\$ 2.209,85 | 4,24% |
| **Visão Tradicional: Desligados Geral (Tudo junto)** | 568.494 | R\$ 2.641,15 | R\$ 2.300,50 | 4,79% |
| --- | --- | --- | --- | --- |
| **1. Admitidos (`+1`)** | 571.139 | **R\$ 2.478,48** | **R\$ 2.209,85** | **4,24%** |
| **2. Pedido de Demissão (`Cód. 40` - Trabalhador saiu)** | 271.098 | **R\$ 2.523,06** | **R\$ 2.241,80** | **4,88%** |
| **3. Demitido pela Empresa (`Cód. 31` - Sem Justa Causa)** | 191.306 | **R\$ 2.962,35** | **R\$ 2.556,00** | **5,80%** |
| **4. Fim de Contrato Temporário (`Cód. 43/45`)** | 81.970 | **R\$ 2.237,10** | **R\$ 2.142,39** | **2,20%** |

#### O que aprendemos com essa prova:
1. **Por que a visão tradicional enganava?**
   Quando misturávamos os `81.970` términos de contrato temporário (`Cód. 43/45`, média de apenas `R$ 2.237,10`) com o restante dos desligamentos, a média geral dos desligados caía para `R$ 2.641,15`, fazendo parecer que a diferença entre admitidos e demitidos era de apenas `-R$ 162,67`.
2. **Prova 1 — O Pedido de Demissão (`Cód. 40`) é movido por Baixa Remuneração e Compressão Salarial:**
   * Os `271.098` trabalhadores que **pediram demissão por conta própria (`Cód. 40`)** tinham mediana salarial de **`R$ 2.241,80`** — apenas **R\$ 31,95 acima da mediana de quem acabou de ser contratado (`R$ 2.209,85`)**!
   * Sem progressão salarial real após a contratação, quase metade dos trabalhadores desligados na indústria catarinense opta voluntariamente por deixar o emprego.
3. **Prova 2 — As empresas estão substituindo mão de obra mais cara e instruída por mais barata (`Cód. 31` vs `Admitidos`):**
   * Quem é **demitido sem justa causa pela empresa (`Cód. 31`)** ganhava em média **`R$ 2.962,35`** (mediana `R$ 2.556,00`) e tinha **`5,80%` de nível superior**, enquanto os novos contratados entram ganhando **`R$ 2.478,48`** (`4,24%` de nível superior) — uma redução salarial média de **`-R$ 483,87` (`-16,3%`)**!

---

### EIXO 3: Qualificação e IA (Macrofamílias de CBOs) — *Quais Profissões Enfrentam cada Gargalo?*

#### Hipótese testada:
*Os gargalos estão em funções operacionais de base ou em cargos técnicos/engenharia, e o motivo de saída muda conforme a família ocupacional?*

#### O que os dados provaram (`database/resultados/eixo3_qualificacao/`):

Cruzando as **Macrofamílias de CBOs** (classificadas a partir das 1.579 ocupações da base) com o **Tipo de Movimentação (`Cód. 40` vs `Cód. 31`)**:

| Macrofamília Ocupacional (IA) | Admitidos (`+1`) | Pedido Demissão (`Cód. 40`) | Demitido Empresa (`Cód. 31`) | Razão `40 / 31` | Salário Médio Pedido (`Cód. 40`) | Diagnóstico do Gargalo |
| :--- | ---: | ---: | ---: | :---: | ---: | :--- |
| **Alimentos e bebidas** | 25.771 | **14.171** | **2.740** | **5,2x** | **R\$ 2.193,29** | **Apagão por Retenção Salarial:** Trabalhador pede conta 5x mais do que é demitido devido ao baixo salário e trabalho frigorífico intenso. |
| **Têxtil, vestuário e couro** | 52.351 | **30.842** | **15.518** | **2,0x** | **R\$ 2.278,12** | **Evasão Voluntária + Retração:** O dobro de pedidos de demissão sobre demissões pela empresa, agravado por salário baixo (`R$ 2.278`). |
| **Produção e apoio industrial** | 163.542 | **81.210** | **43.508** | **1,9x** | **R\$ 2.293,65** | **Gargalo Operacional de Base:** Maior volume do estado; a cada 3 saídas não-temporárias, 2 são pedidos de demissão do próprio operador. |
| **Metalmecânica e metalurgia** | 26.049 | **10.968** | **9.926** | **1,1x** | **R\$ 2.919,63** | **Gargalo Técnico Especializado:** Salário mais alto (`R$ 2.919`), equilíbrio entre saídas e forte disputa por soldadores, torneiros e ferramenteiros. |
| **Construção e infraestrutura** | 94.710 | **36.438** | **39.857** | **0,9x** | **R\$ 2.641,08** | **Ciclo de Obras:** Único grande grupo onde a empresa demite mais (`31`) do que o trabalhador pede conta (`40`), além de `14.020` fins de contrato (`43/45`). |

---

## 4. Conclusão Executiva para o Pitch (A Resposta em 3 Pontos)

1. **Onde está a Expansão Acelerada?**
   Na **Agroindústria de Alimentos (Oeste — Chapecó, Guatambú, Pinhalzinho)**, no complexo **Naval/Logístico/Construção do Litoral Norte (Navegantes, Itajaí)** e no polo **Metalmecânico e Eletroeletrônico (Joinville e Norte)**, além de polos industriais de médio porte no interior (**Agrolândia, Otacílio Costa, São Ludgero e Canoinhas**) que crescem acima de `100 a 280 vagas por 10 mil habitantes`.
2. **Onde e Por Que ocorre o Apagão de Mão de Obra?**
   * **Nos setores de Base Operacional (Agroindústria de Alimentos, Produção Industrial e Têxtil):** O gargalo **não é falta de diploma**, é **retenção salarial (`Código 40`)**. Em Alimentos e Bebidas, há **5,2 vezes mais pedidos de demissão voluntária (`14.171`) do que demissões pela empresa (`2.740`)**, porque a mediana salarial de quem pede conta (`R$ 2.241,80` no estado; `R$ 2.193` em alimentos) está colada no piso de entrada.
   * **Nos setores Técnicos (Metalmecânica, Máquinas e Elétrica/Automação):** Os salários são 30% a 40% maiores (`R$ 2.950 a R$ 3.310`), mas há intensa substituição (`Código 31`) por exigência de qualificação técnica prática.
3. **Recomendações Acionáveis:**
   * **Para Agroindústria e Produção de Base (Oeste e Vale):** Revisão das faixas salariais de progressão após 90/180 dias (descolando a remuneração do piso de entrada) e melhoria de benefícios/ergonomia para estancar os `271 mil` pedidos de demissão (`Código 40`).
   * **Para Metalmecânica, Eletroeletrônica e Polos em Expansão por 10k hab (Norte, Navegantes, Otacílio Costa):** Descentralização de cursos técnicos rápidos de qualificação industrial (SENAI) em soldagem, usinagem CNC, manutenção eletromecânica e automação.
