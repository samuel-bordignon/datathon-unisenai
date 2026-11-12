# Análises do Novo CAGED

Os eixos utilizam Pandas e consomem o CSV unificado da rotina de limpeza existente. Executar na raiz do repositório:

```bash
python -m pip install -r requirements.txt
python src/analises/obter_referencias.py
python src/analises/executar_analises.py
python -m unittest discover -s src/analises -p "test_*.py"
```

As referências públicas do IBGE e do MTE são baixadas uma vez em `database/doc/referencias_analises/`; os scripts analíticos usam os arquivos locais sem acesso à rede. O catálogo versionado de CBOs fica junto dos scripts. O download do MTE é de 2025 e, para cinco códigos sem título no dicionário local e na referência oficial baixada, mantém-se a classificação pendente.

Cada eixo também funciona individualmente:

```bash
python src/analises/eixo1_territorial.py
python src/analises/eixo2_socioeconomico.py
python src/analises/eixo3_qualificacao.py
```

Todos aceitam `--entrada`, `--inicio`, `--fim` e `--saida`. O período padrão é `202509`–`202608`, inclusivo; o caminho padrão de saída é `database/resultados/`. O mínimo nacional está configurado para 2024–2026; outros anos exigem atualização da tabela de mínimos no módulo comum. O executor integrado gera, além das tabelas de cada eixo, auditoria, metadados, inventário das colunas e relatório. As saídas são ignoradas pelo Git e regeneráveis.

## Interpretação e fórmulas

- Admissões = contagem de saldo `+1`; desligamentos = contagem de saldo `-1`; saldo = admissões menos desligamentos; movimentações = soma dos dois fluxos.
- Participações estaduais dividem o valor do grupo pelo total estadual do mesmo tipo e período; tabelas mensais usam totais do mês. Distribuições de escolaridade e faixas dividem pela quantidade do mesmo tipo de movimentação no grupo. As tabelas informam os denominadores.
- Participação de pedidos = desligamentos a pedido / desligamentos do grupo × 100. Cobertura salarial = salários válidos / movimentações do grupo × 100. Saldo por 10.000 habitantes = saldo / população municipal estimada de 2026 × 10.000.
- Salários mensais nominais são considerados válidos entre 0,3 e 150 salários mínimos da competência, inclusive, e apenas para intermitência igual a zero. As contagens de fluxo incluem todos os contratos. Diferença salarial percentual = (média ou mediana dos admitidos − média ou mediana dos desligados) / valor dos desligados × 100.
- Remuneração relativa é a mediana, entre admissões válidas do grupo, dos salários individuais divididos pela mediana estadual de admitidos com a mesma escolaridade e competência. Referências e grupos precisam de 30 salários válidos para sinalização. Não se aplica deflacionamento.
- Crescimento expressivo municipal: saldo positivo e saldo por 10.000 habitantes no quartil superior. No diagnóstico, alta movimentação é volume no quartil superior entre grupos com ao menos 30 movimentações. Um sinal de investigação de retenção combina esse volume, proporção de pedidos acima da estadual e remuneração relativa abaixo de 100%.

As classificações do catálogo foram geradas por aplicação automática de regras semânticas elaboradas por IA sobre títulos ocupacionais; 599 títulos foram classificados amplamente pelo grande grupo CBO e não houve revisão individual. Esse procedimento não equivale a uma classificação individual realizada por um modelo generativo: o catálogo exige revisão antes de conclusões específicas por ocupação. A IA não recebe indicadores de salários ou emprego.

Os registros idênticos são preservados porque a base anonimizada não permite provar duplicação. Os dados descrevem fluxos e escolaridade observada; não medem vagas abertas, exigência de formação, estoque de empregados, tempo de contratação ou causas de desligamento. Os sinais apresentados são hipóteses, sem comprovação de escassez ou dificuldade de contratação.
