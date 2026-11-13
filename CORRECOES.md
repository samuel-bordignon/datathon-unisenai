# Documento de Correções e Melhorias Metodológicas
## Projeto: Raio-X do Mercado de Trabalho Industrial de SC (Datathon 2026)

**Data de atualização:** 13/11/2026
**Status geral:** Implementado

> Este é o documento versionado. A cópia em `database/doc/CORRECOES.md` fica fora do Git (a pasta `database/doc/` é ignorada) e é mantida idêntica.

---

### Item 01: Mesmo setor dividido em várias macrofamílias

**Problema.** A tabela "Combinações que merecem investigação" agrupava por município × setor × macrofamília. O mesmo setor aparecia em mais de uma linha:

- Blumenau | Confecção de artigos do vestuário | Têxtil, vestuário e couro (5.550 movimentações)
- Blumenau | Confecção de artigos do vestuário | Produção e apoio industrial (3.392 movimentações)

**Regra.** No diagnóstico prioritário, cada par município × setor aparece uma única vez.

**Causa.** A macrofamília vem do título da ocupação (CBO), não do setor (CNAE). Ocupações transversais, como alimentador de linha, caem em "Produção e apoio industrial" em qualquer setor.

**Correção adotada.** A macrofamília saiu da chave do diagnóstico (`cenarios.DIMENSOES` e `executar_analises.diagnostico`). Cada linha passa a informar a `macrofamilia_predominante` (a de mais movimentações no par) e o seu percentual. A classificação das ocupações não foi alterada; reclassificar pela CNAE tornaria o Eixo 3 circular, porque a macrofamília passaria a repetir o setor.

**Efeito.** Os polos são recalculados. Blumenau / Vestuário passa a somar cerca de 8.942 movimentações numa única linha. Os números do pitch saem do relatório regenerado.

---

### Item 02: Ordem da escolaridade nos gráficos

**Problema.** Os níveis de escolaridade apareciam em ordem arbitrária (Doutorado no meio, Analfabeto perto do fim).

**Regra.** Gráficos e tabelas de escolaridade seguem a progressão acadêmica.

**Ordem correta (códigos do campo `graudeinstrução` do CAGED):**

| Posição | Código | Nível |
| :---: | :---: | :--- |
| 1 | 1 | Analfabeto |
| 2 | 2 | Até 5ª Incompleto |
| 3 | 3 | 5ª Completo Fundamental |
| 4 | 4 | 6ª a 9ª Fundamental |
| 5 | 5 | Fundamental Completo |
| 6 | 6 | Médio Incompleto |
| 7 | 7 | Médio Completo |
| 8 | 8 | Superior Incompleto |
| 9 | 9 | Superior Completo |
| 10 | **80** | Pós-Graduação completa |
| 11 | **10** | Mestrado |
| 12 | 11 | Doutorado |
| — | 99 | Não Identificado (sempre por último) |

A versão anterior deste documento tratava o código 10 como Pós-Graduação. No dicionário do CAGED, 10 é **Mestrado** e 80 é **Pós-Graduação**. Ordenar pelo número do código empurraria a Pós-Graduação para o fim.

**Correção adotada.** `comum.ORDEM_ESCOLARIDADE` define a ordem acima pelos códigos, e `comum.ordenar_escolaridade()` converte a coluna `escolaridade` em categoria ordenada. O dashboard e o gráfico `escolaridade.png` usam essa ordem.

---

### Item 03: Remoção do gráfico "Volume e saldo relativo"

**Problema.** A dispersão de movimentações × saldo por 10 mil habitantes, na aba territorial, não respondia a nenhuma pergunta do pitch e confundia a leitura.

**Correção adotada.** O gráfico foi removido. A leitura territorial fica no mapa (saldo absoluto ou por 10 mil habitantes) e nas barras divergentes dos 5 maiores e 5 menores saldos. O painel passou de 6 para 4 abas, uma por bloco do pitch de 3 minutos.

---

### Item 04: Números do pitch alinhados aos resultados

**Problema.** O roteiro e a apresentação citavam valores que não batiam com os CSVs ou que diziam mais do que os dados mostram.

| Afirmação anterior | Correção |
| :--- | :--- |
| Ensino Médio: pedido R$ 2.241 vs. admitido R$ 2.209 | Esses são valores de todos os níveis. No Médio Completo: admitido R$ 2.240,91, pedido R$ 2.256,70, demissão pela empresa R$ 2.543,20 (medianas). |
| Deságio de −16,3% | É a diferença de médias. Pela mediana, −13,5%. O painel informa qual medida usa. |
| "60%+ das vagas são de Ensino Médio" | O CAGED mede admissões, não vagas: 56,8% das admissões são Médio Completo. |
| "Comprova compressão salarial" | A diferença entre entrada e saída cresce com a escolaridade. É compatível com compressão salarial ou com maior tempo de casa de quem sai; os dados não separam as duas explicações. |
| "Não faltam engenheiros" | O saldo negativo de Gestão e Engenharia pode refletir promoções internas, que o CAGED não registra como admissão. |
| Desligamentos em 3 motivos | Passam a 4: pedido (40), empresa sem justa causa (31), fim de contrato (43/45) e outros. Fim de contrato é 14,4% dos desligamentos. |

**Correção adotada.** Os números do painel são calculados sobre o recorte filtrado. Valores fixos no pitch indicam "SC, período completo".

---

### Registro de histórico
- **12/11/2026 23:25:** Item 01 registrado.
- **12/11/2026 23:33:** Item 02 registrado.
- **13/11/2026:** Item 02 corrigido (código 80 = Pós-Graduação, 10 = Mestrado); Itens 03 e 04 registrados; Itens 01 a 04 implementados.
