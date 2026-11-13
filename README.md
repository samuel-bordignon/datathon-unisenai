# Datathon 2026 — Raio-X do Mercado de Trabalho e Vagas Industriais em SC

Projeto desenvolvido durante a Semana Acadêmica do **Bacharelado em Ciência de Dados e Inteligência Artificial (UniSENAI)** com o objetivo de diagnosticar polos em expansão acelerada e gargalos de mão de obra no setor industrial de Santa Catarina a partir dos microdados do **Novo CAGED** e indicadores demográficos do **IBGE**.

---

## Pergunta Central de Negócio
> *“Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?”*

---

## Estrutura do Repositório

* [`database/doc/`](./database/doc/): Diretório para armazenamento local das bases de dados brutas e da base limpa unificada (ignorado no Git para arquivos pesados).
* [`src/limpeza/`](./src/limpeza/): Módulos Python responsáveis pela ingestão, limpeza, filtragem do setor industrial, cruzamento relacional (`Inner Join`) e exportação do CSV unificado.
  * Consulte a documentação detalhada das decisões de limpeza em: **[`src/limpeza/README.md`](./src/limpeza/README.md)**.

---

## Como Executar a Limpeza

```bash
python src/limpeza/pipeline_limpeza.py
```

## Cenários de negócio e dashboard

Instale as dependências e prepare a base analítica uma vez após cada atualização dos dados:

```bash
python -m pip install -r requirements.txt
python src/analises/obter_referencias.py
python src/analises/executar_analises.py
python src/analises/preparar_dashboard.py
streamlit run dashboard.py
```

A preparação usa o CSV unificado e as mesmas regras de enriquecimento dos eixos. Por padrão, contempla as competências 202509 a 202608; aceita `--entrada`, `--inicio`, `--fim` e `--saida`, como os demais scripts. O dashboard lê `database/resultados/dashboard/movimentacoes.parquet` e seus metadados; se usar outra saída, copie os arquivos para esse diretório. Os dados processados são ignorados pelo Git e devem ser gerados localmente. A malha municipal vem das referências locais do IBGE.

### As 4 abas do painel

| Aba | Pergunta | Conteúdo |
| :--- | :--- | :--- |
| 1. Territorial e setorial | Onde o emprego cresce e onde encolhe? | 4 KPIs, mapa (saldo absoluto ou por 10 mil hab.), saldo mensal com acumulado, 5 maiores e 5 menores saldos por município e setor |
| 2. Perfil e remuneração | Quem entra, quem sai e quanto ganha? | Escolaridade (ordem acadêmica) e faixa etária com desligamentos pelos 4 motivos; salário mediano de admitidos, pedidos e demitidos pela empresa |
| 3. Qualificação e IA | As saídas estão na base ou nas funções técnicas? | Nível de atuação (grande grupo CBO) ou macrofamília por motivo; CBOs com maior déficit |
| 4. Diagnóstico e ações | Resposta à pergunta central | Cartões calculados no recorte, polos críticos (um por município × setor), recomendações ligadas às macrofamílias, hipóteses e chat com Gemini |

### IA com Google Gemini: onde colocar a chave

1. Gere a chave em <https://aistudio.google.com/apikey>.
2. **Dashboard:** copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha `GEMINI_API_KEY`. O `secrets.toml` está no `.gitignore`; nunca versione a chave.
3. **Scripts (ou alternativa ao arquivo):** defina a variável de ambiente. No PowerShell: `$env:GEMINI_API_KEY = "sua-chave"`.
4. Opcional: `GEMINI_MODEL` (padrão `gemini-3.5-flash-lite`, o de menor custo; alternativa `gemini-4-hydrogen`).

Sem chave, o painel funciona normalmente e a seção de IA mostra como configurá-la. A chamada usa a API REST `generateContent` com a chave no header `x-goog-api-key` (código em `src/ia/gemini.py`). O Gemini recebe apenas tabelas agregadas do recorte (`src/ia/contexto.py`), nunca microdados.

Validação do catálogo de CBOs com o Gemini (opcional, retomável; grava `database/resultados/ia/`, exibido na aba 3):

```powershell
$env:GEMINI_API_KEY = "sua-chave"
python src/analises/validar_catalogo_llm.py --pausa 4
```

O painel filtra competência, região imediata do IBGE, município e divisão CNAE. O quartil de movimentação e a taxa de pedidos são calculados para SC no período selecionado; o sinal de retenção combina os critérios descritos em [Análises do Novo CAGED](src/analises/README.md). A expansão relativa usa o quartil estadual do saldo municipal por 10 mil habitantes, com a população estimada de 2026. Valores percentuais são apresentados com seus denominadores; salário relativo usa a referência estadual da mesma escolaridade e competência. Medianas são calculadas a partir dos registros selecionados. Variações percentuais mensais são omitidas quando o valor anterior é zero ou negativo.

As medidas representam fluxos, não vagas abertas, estoque de trabalhadores ou causas. Escolaridade é a observada no trabalhador e não indica exigência da vaga. Os salários são nominais e sujeitos aos filtros de elegibilidade documentados nos eixos. Os agrupamentos de CBO usam regras semânticas elaboradas com IA, aplicadas automaticamente e sem revisão individual; os resultados exigem validação. Recomendações são hipóteses de investigação, não prova de escassez ou causalidade.

Para verificar os cálculos e executar todas as abas do painel sem abrir o navegador:

```bash
python -m unittest discover -s src/analises -p "test_*.py"
python src/teste_dashboard_abas.py
```

### Roteiro de pitch (3 minutos)

Uma aba por bloco: 50 s (aba 1) + 50 s (aba 2) + 50 s (aba 3) + 30 s (aba 4). Fala completa em [`apresentacao/ROTEIRO_PITCH_3_MINUTOS.md`](apresentacao/ROTEIRO_PITCH_3_MINUTOS.md). Correções metodológicas em [`CORRECOES.md`](CORRECOES.md).
