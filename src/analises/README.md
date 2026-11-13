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
- O diagnóstico agrupa por município × divisão CNAE (uma linha por par). A macrofamília não entra na chave; cada linha informa a macrofamília predominante e sua participação no par (Item 01 de `CORRECOES.md`).
- Motivos de desligamento, mutuamente exclusivos e somando os desligamentos: pedido do trabalhador (`tipomovimentação` 40), demissão sem justa causa pela empresa (31), fim de contrato (43 e 45) e outros (justa causa, acordo, aposentadoria, morte, transferência e ignorados).
- Faixa etária: até 17, 18–24, 25–34, 35–44, 45–54 e 55 anos ou mais; idade ausente fica em "Não informada". Nível de atuação pelo primeiro dígito da CBO 2002: 1–3 gestão, engenharia e técnicos; 4–6 apoio administrativo e serviços; 7–9 operacional de base.
- Escolaridade segue a progressão acadêmica pelos códigos `1, 2, 3, 4, 5, 6, 7, 8, 9, 80, 10, 11, 99`: no CAGED, 80 é Pós-Graduação e 10 é Mestrado.
- Deságio por escolaridade = (mediana dos admitidos − mediana do grupo de saída) / mediana do grupo de saída × 100, calculado para pedidos (40) e demissões pela empresa (31). Grupos com menos de 30 salários válidos ficam marcados como amostra insuficiente.

As classificações do catálogo foram geradas por aplicação automática de regras semânticas elaboradas por IA sobre títulos ocupacionais; 599 títulos foram classificados amplamente pelo grande grupo CBO e não houve revisão individual. O script `validar_catalogo_llm.py` envia só código e título das CBOs ao Gemini, pede uma classificação independente nas mesmas 19 macrofamílias e grava a concordância (simples e ponderada pelas movimentações) em `database/resultados/ia/`; o catálogo não é alterado. No painel, o gerador de hipóteses e o chat recebem apenas tabelas agregadas do recorte, nunca microdados.

Os registros idênticos são preservados porque a base anonimizada não permite provar duplicação. Os dados descrevem fluxos e escolaridade observada; não medem vagas abertas, exigência de formação, estoque de empregados, tempo de contratação ou causas de desligamento. Os sinais apresentados são hipóteses, sem comprovação de escassez ou dificuldade de contratação.
