# Roteiro do pitch de 3 minutos

Uma aba do painel por bloco. Números de **SC, período completo** (09/2025 a 08/2026), sem filtros; se a banca filtrar, o painel recalcula e a fala deve seguir a tela.

Antes de começar: `streamlit run dashboard.py`, filtros vazios, aba 1 aberta. Para a aba 4, gere as hipóteses com IA uma vez antes do pitch (a resposta fica em cache).

---

## Aba 1 · Territorial e setorial (~50 s)

**Pergunta:** onde o emprego industrial cresce e onde encolhe?

> "Analisamos 1,14 milhão de movimentações do Novo CAGED na indústria de SC. O saldo do estado é de só +2.645, mas por trás dele houve 571 mil admissões e 568 mil desligamentos, e 47,7% dessas saídas foram pedidos do próprio trabalhador.
> No mapa, a expansão está no litoral norte e no oeste: Navegantes lidera com +2.765, ou 281 por 10 mil habitantes, seguida de Joinville (+1.527) e Chapecó (+1.110). A retração está em São José (−990) e no Vale do Itajaí, com Blumenau (−842) e Gaspar (−535).
> Por setor, alimentos (+4.739) e máquinas elétricas (+2.018) crescem; vestuário (−4.571), madeira e móveis encolhem."

Apontar: os 4 cartões, o mapa, as barras azuis e vermelhas.

## Aba 2 · Perfil e remuneração (~50 s)

**Pergunta:** quem entra, quem sai e quanto ganha?

> "56,8% das admissões são de Ensino Médio Completo. Os jovens pedem mais demissão: 50,5% das saídas entre 18 e 34 anos são pedidos, contra 42,1% a partir dos 45 anos, em que pesa mais a demissão pela empresa.
> No salário, quem pede demissão ganha mediana de R$ 2.242, praticamente o mesmo que quem entra, R$ 2.210: permanecer quase não rende mais. Quem é demitido pela empresa ganhava R$ 2.556, e quem entra recebe 13,5% menos. Essa diferença cresce com a escolaridade, de −8% no analfabeto a −21% no superior completo. É compatível com compressão salarial ou com o tempo de casa de quem sai; o CAGED não separa as duas."

Apontar: barras na ordem acadêmica, legenda dos 4 motivos, percentuais em vermelho no gráfico de salários.

## Aba 3 · Qualificação e IA (~50 s)

**Pergunta:** as saídas estão em funções técnicas ou na base operacional?

> "Agrupamos 1.578 ocupações em 19 macrofamílias com regras elaboradas por IA e validamos com uma classificação independente do Gemini [citar a concordância mostrada na aba, se a validação tiver sido executada].
> A base operacional concentra 76% das movimentações e 77% dos pedidos de demissão. As ocupações com maior déficit são operador de máquinas fixas, inspetor de qualidade e costureiros, quase todas com o pedido do trabalhador como principal motivo de saída.
> Gestão e engenharia têm saldo negativo, mas isso pode refletir promoções internas, que o CAGED não registra como admissão."

Apontar: alternar "Nível de atuação" e "Macrofamília (IA)"; o gráfico de déficit por CBO.

## Aba 4 · Diagnóstico e ações (~30 s)

> "Nossa resposta: a indústria cresce nos polos portuário e agroindustrial, e o gargalo principal sugerido pelos dados é de retenção na base operacional. O caso mais forte é Concórdia, na indústria de alimentos: 68,9% dos desligamentos são pedidos e quem entra recebe 10,7% abaixo da referência estadual.
> Propomos três ações, cada uma ligada a uma macrofamília: degraus salariais aos 6, 12 e 24 meses na produção, alimentos e têxtil; trilhas SENAI nas ocupações com maior déficit; e atração de talentos regionais nos polos de expansão. Obrigado."

Apontar: os três cartões, a tabela de polos críticos e, se houver tempo, um cartão de hipótese do Gemini.

---

## Respostas prontas para a banca

- **"Isso prova apagão?"** Não. O CAGED mede fluxos, não vagas abertas nem tempo de contratação. Os sinais combinam volume, pedidos e salário e indicam onde investigar.
- **"Por que a macrofamília aparece como predominante?"** Para não dividir o mesmo setor em várias linhas (Item 01 de `CORRECOES.md`).
- **"Como a IA foi usada?"** Em três pontos: regras de classificação das CBOs, validação independente pelo Gemini e geração de hipóteses e chat no painel, sempre com dados agregados.
- **"O saldo por 10 mil habitantes de Guatambú (598) não é exagerado?"** Em municípios pequenos uma empresa muda muito o valor; por isso o mapa também mostra o saldo absoluto.
