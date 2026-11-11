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
