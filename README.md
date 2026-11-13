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

O painel filtra competência, região imediata do IBGE, município e divisão CNAE. O quartil de movimentação e a taxa de pedidos são calculados para SC no período selecionado; o sinal de retenção combina os critérios descritos em [Análises do Novo CAGED](src/analises/README.md). A expansão relativa usa o quartil estadual do saldo municipal por 10 mil habitantes, com a população estimada de 2026. Valores percentuais são apresentados com seus denominadores; salário relativo usa a referência estadual da mesma escolaridade e competência. Medianas são calculadas a partir dos registros selecionados. Variações percentuais mensais são omitidas quando o valor anterior é zero ou negativo.

As medidas representam fluxos, não vagas abertas, estoque de trabalhadores ou causas. Escolaridade é a observada no trabalhador e não indica exigência da vaga. Os salários são nominais e sujeitos aos filtros de elegibilidade documentados nos eixos. Os agrupamentos de CBO usam regras semânticas elaboradas com IA, aplicadas automaticamente e sem revisão individual; os resultados exigem validação. Recomendações são hipóteses de investigação, não prova de escassez ou causalidade.

Para verificar os cálculos:

```bash
python -m unittest discover -s src/analises -p "test_*.py"
```

### Roteiro de pitch (3 minutos)

1. **30 segundos:** apresente a pergunta central, período e volume de admissões, desligamentos e saldo na visão geral.
2. **45 segundos:** mostre os municípios com maior saldo absoluto e relativo e os setores que contribuem para o crescimento.
3. **60 segundos:** apresente os grupos com sinais combinados, seus denominadores, comparação salarial e escolaridade; ressalte que são hipóteses.
4. **45 segundos:** proponha investigação junto às empresas dos grupos identificados, revisão das faixas e validação de necessidades de formação relacionadas às macrofamílias observadas.
