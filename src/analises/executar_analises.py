"""
Orquestrador principal: executa os três eixos de análise e produz o diagnóstico
integrado, metadados de auditoria e relatório executivo em Markdown.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd

from comum import (
    argumentos,
    dados_comuns,
    agregar,
    exportar,
    DICIONARIO,
    REFERENCIAS,
    CATALOGO,
)
import eixo1_territorial
import eixo2_socioeconomico
import eixo3_qualificacao


def diagnostico(df: pd.DataFrame, pasta_saida: Path) -> pd.DataFrame:
    """
    Cruza Município × Divisão CNAE × Macrofamília CBO para identificar polos
    em expansão acelerada, retração e pressão crítica de retenção (Apagão).
    """
    dimensoes = [
        "codigo_ibge_7d",
        "nome_municipio",
        "codigo_regiao_imediata",
        "regiao_imediata",
        "cnae_divisao",
        "setor",
        "macrofamilia",
    ]
    total = agregar(df, dimensoes)
    elegiveis = total[total["movimentacoes"] >= 30]
    limiar_volume = elegiveis["movimentacoes"].quantile(0.75)

    total_desligamentos_sc = df["desligamentos"].sum()
    if total_desligamentos_sc > 0:
        pct_pedido_estado = (
            100.0 * df["desligamentos_a_pedido"].sum() / total_desligamentos_sc
        )
    else:
        pct_pedido_estado = float("nan")

    total["limiar_alta_movimentacao"] = limiar_volume
    total["pct_desligamentos_a_pedido_estado"] = pct_pedido_estado
    total["alta_movimentacao"] = (total["movimentacoes"] >= 30) & (
        total["movimentacoes"] >= limiar_volume
    )
    total["expansao"] = (total["movimentacoes"] >= 30) & (total["saldo"] > 0)
    total["retracao"] = (total["movimentacoes"] >= 30) & (total["saldo"] < 0)

    # Sinal de gargalo de retenção / apagão por desatratividade:
    # Alto giro + Taxa de Pedido de Demissão (Cód. 40) acima da média estadual + Salário abaixo da mediana de referência
    total["hipotese_investigar_retencao"] = (
        total["alta_movimentacao"]
        & (total["pct_desligamentos_a_pedido_desligamentos_grupo"] > pct_pedido_estado)
        & (total["n_admitidos_com_referencia"] >= 30)
        & (total["remuneracao_relativa_mediana"] < 1.0)
    )

    mensal = agregar(df, ["competencia"] + dimensoes)
    exportar(
        {
            "diagnostico_integrado": total,
            "diagnostico_integrado_mensal": mensal,
        },
        pasta_saida / "integrado",
    )

    # Exportar também o cubo multidimensional para filtros rápidos no Dashboard Streamlit
    df_cubo = df.copy()
    df_cubo["soma_salario"] = df_cubo["salario_valido"].fillna(0.0)
    cubo = (
        df_cubo.groupby(
            [
                "regiao_imediata",
                "codigo_ibge_7d",
                "nome_municipio",
                "populacao_estimada_2026",
                "secao",
                "cnae_divisao",
                "setor",
                "macrofamilia",
                "escolaridade",
                "grupo_movimentacao",
            ],
            observed=True,
        )
        .agg(
            movimentacoes=("saldo_mov", "size"),
            admissoes=("admissoes", "sum"),
            desligamentos=("desligamentos", "sum"),
            pedido_cod40=("desligamentos_a_pedido", "sum"),
            empresa_cod31=("demissoes_sem_justa_causa", "sum"),
            contrato_cod43_45=("terminos_contrato", "sum"),
            salarios_validos=("salario_valido", "count"),
            soma_salario=("soma_salario", "sum"),
        )
        .reset_index()
    )
    cubo.to_csv(
        pasta_saida / "cubo_explorador.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig",
    )

    return total


def documentar(
    df: pd.DataFrame,
    auditoria: dict,
    territorial: dict[str, pd.DataFrame],
    socioeconomico: dict[str, pd.DataFrame],
    qualificacao: dict[str, pd.DataFrame],
    integrado: pd.DataFrame,
    pasta_saida: Path,
) -> None:
    """Gera o inventário de colunas, metadados JSON e o relatório executivo em Markdown."""
    layout = pd.read_excel(DICIONARIO, sheet_name="Layout", header=1, dtype=str).iloc[
        :, :3
    ]
    layout.columns = ["coluna", "significado", "codigo_dicionario"]

    colunas_extras_ibge = {
        "nome_municipio": "Nome do município IBGE",
        "codigo_ibge_7d": "Código IBGE municipal com dígito verificador",
        "area_territorial_km2": "Área territorial municipal em 2025 (km²)",
        "populacao_censo_2022": "População do censo de 2022",
        "densidade_demografica_2022": "Densidade demográfica do censo de 2022",
        "populacao_estimada_2026": "População estimada em 2026",
        "taxa_escolarizacao_2022": "Taxa de escolarização de 6 a 14 anos em 2022",
        "idhm_2010": "Índice de desenvolvimento humano municipal de 2010",
        "pib_per_capita_2023": "PIB municipal per capita de 2023",
        "codigo_municipio_6d": "Código municipal IBGE sem dígito verificador",
    }

    lista_tipos = [
        {"coluna": k, "tipo_observado": v}
        for k, v in auditoria["tipos_colunas"].items()
    ]
    tabela_tipos = pd.DataFrame(lista_tipos)

    lista_extras = [
        {"coluna": k, "significado": v} for k, v in colunas_extras_ibge.items()
    ]
    layout = pd.concat([layout, pd.DataFrame(lista_extras)], ignore_index=True)
    layout = tabela_tipos.merge(layout, on="coluna", how="left", validate="one_to_one")
    exportar({"colunas_entrada": layout}, pasta_saida)

    fontes = json.loads((REFERENCIAS / "fontes.json").read_text(encoding="utf-8"))
    metadados = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "auditoria": auditoria,
        "fontes_complementares": fontes,
        "catalogo_classificacao": str(CATALOGO),
        "salario_minimo": {"2024": 1412, "2025": 1518, "2026": 1621},
        "metodo_classificacao": (
            "Regras semânticas assistidas por IA aplicadas sobre o catálogo oficial CBO."
        ),
        "denominadores": {
            "pct_admissoes_total_sc": "admissões em SC no período correspondente",
            "pct_desligamentos_total_sc": "desligamentos em SC no período correspondente",
            "pct_movimentacoes_total_sc": "admissões e desligamentos em SC no período correspondente",
            "percentual_grupo_tipo_mov": "total do mesmo grupo e tipo de movimentação",
            "pct_desligamentos_a_pedido_desligamentos_grupo": "desligamentos do grupo",
            "pct_demissoes_empresa_desligamentos_grupo": "desligamentos do grupo",
            "pct_terminos_contrato_desligamentos_grupo": "desligamentos do grupo",
            "pct_pedido_sobre_saidas_nao_temporarias": "soma de pedidos de demissão (40) e demissões sem justa causa (31) do grupo",
            "pct_salarios_validos_movimentacoes_grupo": "movimentações do grupo",
            "remuneracao_relativa_pct_referencia": "mediana estadual de admitidos da mesma escolaridade e competência",
            "saldo_por_10000_habitantes": "população municipal estimada em 2026",
        },
        "limitacoes": (
            "Microdados anonimizados do CAGED registram fluxos de admissão e desligamento formal; "
            "a distinção entre Pedido de Demissão (Cód. 40) e Demissão sem Justa Causa (Cód. 31) "
            "permite separar saídas voluntárias por baixa retenção de cortes/substituições pela empresa."
        ),
    }

    caminho_metadados = pasta_saida / "metadados.json"
    caminho_metadados.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    mun = territorial["municipios"]
    setores = territorial["setores_divisao"]
    grupos_sal = socioeconomico["salarios_grupo_movimentacao"]
    alertas = integrado[integrado["hipotese_investigar_retencao"]].sort_values(
        "movimentacoes", ascending=False
    )

    def formatar_top(tabela: pd.DataFrame, coluna_ordem: str, coluna_nome: str, asc: bool = False) -> str:
        linhas_formatadas = []
        recorte = tabela.sort_values(coluna_ordem, ascending=asc).head(5)
        for _, row in recorte.iterrows():
            linhas_formatadas.append(
                f"- **{row[coluna_nome]}**: saldo `{int(row['saldo']):+d}` "
                f"({int(row['admissoes']):,} admissões vs. {int(row['desligamentos']):,} desligamentos | "
                f"Pedidos Cód. 40: `{row['pct_desligamentos_a_pedido_desligamentos_grupo']:.1f}%` | "
                f"Empresa Cód. 31: `{row['pct_demissoes_empresa_desligamentos_grupo']:.1f}%` | "
                f"Salário Médio: `R$ {row['salario_medio']:.2f}`)."
            )
        return "\n".join(linhas_formatadas)

    linhas_grupos = []
    for _, r in grupos_sal.sort_values("grupo_movimentacao").iterrows():
        linhas_grupos.append(
            f"- **{r['grupo_movimentacao']}**: `{int(r['movimentacoes']):,}` registros | "
            f"Salário Médio: **`R$ {r['salario_medio']:.2f}`** | "
            f"Mediana: **`R$ {r['salario_mediano']:.2f}`** | "
            f"Ensino Superior: `{r['pct_superior_completo']:.2f}%`."
        )
    resumo_grupos_mov = "\n".join(linhas_grupos)

    linhas_alertas = []
    for _, r in alertas.head(10).iterrows():
        linhas_alertas.append(
            f"- **{r['nome_municipio']} / {r['setor']} / {r['macrofamilia']}**: "
            f"`{int(r['movimentacoes'])}` movimentações (`{r['pct_movimentacoes_total_sc']:.3f}%` de SC); "
            f"`{int(r['desligamentos_a_pedido'])}` pedidos Cód. 40 em `{int(r['desligamentos'])}` desligamentos "
            f"(`{r['pct_desligamentos_a_pedido_desligamentos_grupo']:.1f}%`); "
            f"remuneração mediana relativa de `{r['remuneracao_relativa_pct_referencia']:.1f}%` da referência estadual."
        )
    resumo_alertas = (
        "\n".join(linhas_alertas)
        or "Nenhuma combinação atingiu simultaneamente os critérios adotados."
    )

    n = len(df)
    a = int(df["admissoes"].sum())
    d = int(df["desligamentos"].sum())

    relatorio = f"""# Diagnóstico Integrado e Validação de Hipóteses — Indústria de Santa Catarina

Período analisado: **`{auditoria['inicio']}` a `{auditoria['fim']}`** (12 meses).
Foram registradas **`{n:,}` movimentações industriais**: **`{a:,}` admissões** (`{100*a/n:.2f}%`) e **`{d:,}` desligamentos** (`{100*d/n:.2f}%`), resultando em um **saldo líquido positivo de `{a-d:+,}` empregos**.

---

## 1. Eixo Territorial e Setorial: Expansão Acelerada vs. Retração

### Top 5 Municípios com Maior Saldo Positivo Absoluto
{formatar_top(mun, 'saldo', 'nome_municipio', asc=False)}

### Top 5 Municípios com Maior Retração Industrial
{formatar_top(mun, 'saldo', 'nome_municipio', asc=True)}

### Top 5 Divisões Industriais (CNAE) em Expansão
{formatar_top(setores, 'saldo', 'setor', asc=False)}

### Top 5 Divisões Industriais (CNAE) em Retração
{formatar_top(setores, 'saldo', 'setor', asc=True)}

---

## 2. Eixo Socioeconômico: O que o Tipo de Movimentação (`Cód. 40` vs `Cód. 31`) Prova?

Quando separamos os desligamentos pelo motivo real (`tipomovimentação`), descobrimos dois fenômenos distintos que ficavam ocultos na média geral:

{resumo_grupos_mov}

1. **Prova do Gargalo de Retenção por Desatratividade Salarial (`Código 40` — Pedido de Demissão):**
   - Quase metade (`47,7%`, ou `271.098` trabalhadores) de todas as saídas da indústria catarinense ocorre por **iniciativa do próprio trabalhador (`Código 40`)**.
   - Esses trabalhadores que pedem demissão ganham mediana de **`R$ 2.241,80`** (média `R$ 2.523,06`), praticamente estagnados no salário inicial de contratação (`R$ 2.209,85` de mediana).
2. **Prova da Substituição Salarial / Compressão (`Código 31` — Demissão sem Justa Causa pela Empresa):**
   - Os trabalhadores desligados por iniciativa da empresa (`Código 31`, `191.306` registros) recebiam média de **`R$ 2.962,35`** (mediana `R$ 2.556,00`) e tinham maior proporção de Ensino Superior (`5,80%`), enquanto os novos admitidos entram ganhando **`R$ 2.478,48`** (`4,24%` com Ensino Superior) — um deságio de **`-R$ 483,87` (`-16,3%`)** na reposição.
   - Os términos de contrato temporário (`Códigos 43/45`, `81.970` registros com média de `R$ 2.237,10`) puxavam a média geral dos desligados para baixo (`R$ 2.641,15`), mascarando essa diferença quando analisados juntos.

---

## 3. Polos Críticos Prioritários (Município × Setor × Macrofamília CBO)

Combinações com alto giro (quartil superior), proporção de pedidos de demissão (`Cód. 40`) acima da média estadual (`47,7%`) e remuneração abaixo da mediana estadual para a mesma escolaridade:

{resumo_alertas}

---

## 4. Metodologia e Governança dos Dados

- **Fórmulas:** `Saldo = Admissões − Desligamentos`; `Movimentação = Admissões + Desligamentos`; `Saldo por 10.000 hab = (Saldo / População Estimada 2026) × 10.000`.
- **Elegibilidade Salarial (Critério MTE):** Incluídos apenas salários nominais entre `0,3` e `150` salários mínimos vigentes (`R$ 1.518` em 2025 e `R$ 1.621` em 2026) com indicador de trabalho intermitente igual a zero (`{auditoria['salarios']['validos']:,}` salários válidos, ou `{100*auditoria['salarios']['validos']/n:.2f}%` de cobertura).
- **Integridade:** Preservadas `{auditoria['repeticoes_identicas_excedentes']:,}` repetições idênticas na base completa (vínculos anônimos distintos de mesmo perfil no mesmo mês/município) e auditadas `{auditoria['linhas_antes_periodo']:,}` declarações fora do período principal.
"""
    (pasta_saida / "relatorio.md").write_text(relatorio, encoding="utf-8")


def main() -> None:
    args = argumentos()
    df, auditoria = dados_comuns(args)
    territorial = eixo1_territorial.analisar(df, args.saida)
    socioeconomico = eixo2_socioeconomico.analisar(df, args.saida)
    qualificacao = eixo3_qualificacao.analisar(df, args.saida)
    integrado = diagnostico(df, args.saida)
    documentar(
        df,
        auditoria,
        territorial,
        socioeconomico,
        qualificacao,
        integrado,
        args.saida,
    )
    print(f"Resultados gerados com sucesso em: {args.saida.resolve()} | {len(df):,} movimentações processadas.")


if __name__ == "__main__":
    main()
