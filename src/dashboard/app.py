"""
Dashboard Analítico Interativo (Streamlit) — Raio-X do Mercado de Trabalho Industrial em SC.
Permite filtrar por Região Imediata, Município, Setor Industrial (CNAE), Macrofamília (CBO)
e Escolaridade, comparando a Visão Tradicional com o Paradigma por Tipo de Movimentação (40, 31, 43/45).
"""
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Raio-X Industrial de SC — Datathon 2026",
    page_icon="🏭",
    layout="wide",
)

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_CUBO = RAIZ / "database" / "resultados" / "cubo_explorador.csv"
CAMINHO_MUNICIPIOS_RESUMO = (
    RAIZ / "database" / "resultados" / "eixo1_territorial" / "municipios.csv"
)
CAMINHO_MAPA_PNG = (
    RAIZ / "database" / "resultados" / "eixo1_territorial" / "mapa_saldo.png"
)


@st.cache_data
def carregar_cubo() -> pd.DataFrame:
    """Carrega o cubo multidimensional pré-agregado para filtragem instantânea."""
    df = pd.read_csv(CAMINHO_CUBO, sep=";", encoding="utf-8-sig")
    return df


@st.cache_data
def carregar_pop_municipios() -> pd.DataFrame:
    """Carrega a tabela de população única por município para o denominador de 10.000 hab."""
    df_mun = pd.read_csv(CAMINHO_MUNICIPIOS_RESUMO, sep=";", encoding="utf-8-sig")
    return df_mun[
        ["codigo_ibge_7d", "nome_municipio", "populacao_estimada_2026"]
    ].drop_duplicates("codigo_ibge_7d")


def agregar_recorte(df_filtrado: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Agrega qualquer subconjunto filtrado do cubo calculando saldos, taxas 40/31 e salários."""
    if df_filtrado.empty:
        return pd.DataFrame()

    if chaves:
        agrupado = (
            df_filtrado.groupby(chaves, dropna=False, observed=True)
            .agg(
                movimentacoes=("movimentacoes", "sum"),
                admissoes=("admissoes", "sum"),
                desligamentos=("desligamentos", "sum"),
                pedido_cod40=("pedido_cod40", "sum"),
                empresa_cod31=("empresa_cod31", "sum"),
                contrato_cod43_45=("contrato_cod43_45", "sum"),
                salarios_validos=("salarios_validos", "sum"),
                soma_salario=("soma_salario", "sum"),
            )
            .reset_index()
        )
    else:
        agrupado = pd.DataFrame(
            [
                {
                    "movimentacoes": df_filtrado["movimentacoes"].sum(),
                    "admissoes": df_filtrado["admissoes"].sum(),
                    "desligamentos": df_filtrado["desligamentos"].sum(),
                    "pedido_cod40": df_filtrado["pedido_cod40"].sum(),
                    "empresa_cod31": df_filtrado["empresa_cod31"].sum(),
                    "contrato_cod43_45": df_filtrado["contrato_cod43_45"].sum(),
                    "salarios_validos": df_filtrado["salarios_validos"].sum(),
                    "soma_salario": df_filtrado["soma_salario"].sum(),
                }
            ]
        )

    agrupado["saldo"] = agrupado["admissoes"] - agrupado["desligamentos"]
    deslig_valido = agrupado["desligamentos"].replace(0, float("nan"))
    agrupado["pct_pedido_cod40"] = (agrupado["pedido_cod40"] / deslig_valido) * 100.0
    agrupado["pct_empresa_cod31"] = (agrupado["empresa_cod31"] / deslig_valido) * 100.0
    agrupado["pct_contrato_cod43_45"] = (
        agrupado["contrato_cod43_45"] / deslig_valido
    ) * 100.0

    sal_valido = agrupado["salarios_validos"].replace(0, float("nan"))
    agrupado["salario_medio"] = agrupado["soma_salario"] / sal_valido

    empresa_nao_zero = agrupado["empresa_cod31"].replace(0, float("nan"))
    agrupado["razao_40_sobre_31"] = agrupado["pedido_cod40"] / empresa_nao_zero

    return agrupado


def main() -> None:
    st.title("🏭 Painel de Inteligência Operacional e Territorial — Indústria SC")
    st.caption(
        "Datathon UniSENAI 2026 | Microdados do Novo CAGED (Set/2025 a Ago/2026) cruzados com IBGE e Catálogo de CBOs IA"
    )

    if not CAMINHO_CUBO.exists():
        st.error(
            f"Arquivo de cubo não encontrado em {CAMINHO_CUBO}. Execute a preparação primeiro."
        )
        return

    cubo = carregar_cubo()
    pop_municipios = carregar_pop_municipios()

    # =========================================================================
    # BARRA LATERAL: FILTROS MULTIDIMENSIONAIS
    # =========================================================================
    st.sidebar.header("🔍 Filtros de Investigação")
    st.sidebar.markdown(
        "Selecione qualquer combinação de **Região, Município, Setor, Macrofamília ou Escolaridade** para comprovar os dados em tempo real:"
    )

    opcoes_regiao = sorted(cubo["regiao_imediata"].dropna().unique().tolist())
    regioes_sel = st.sidebar.multiselect(
        "1. Região Geográfica Imediata (IBGE):",
        options=opcoes_regiao,
        default=[],
        placeholder="Todas as 24 regiões de SC",
    )

    cubo_pos_regiao = (
        cubo[cubo["regiao_imediata"].isin(regioes_sel)] if regioes_sel else cubo
    )

    opcoes_municipio = sorted(
        cubo_pos_regiao["nome_municipio"].dropna().unique().tolist()
    )
    municipios_sel = st.sidebar.multiselect(
        "2. Município(s):",
        options=opcoes_municipio,
        default=[],
        placeholder="Todos os municípios do recorte",
    )

    opcoes_setor = sorted(cubo["setor"].dropna().unique().tolist())
    setores_sel = st.sidebar.multiselect(
        "3. Setor Industrial (Divisão CNAE):",
        options=opcoes_setor,
        default=[],
        placeholder="Todos os setores industriais",
    )

    opcoes_macro = sorted(cubo["macrofamilia"].dropna().unique().tolist())
    macros_sel = st.sidebar.multiselect(
        "4. Macrofamília Ocupacional (CBO IA):",
        options=opcoes_macro,
        default=[],
        placeholder="Todas as macrofamílias",
    )

    opcoes_esc = sorted(cubo["escolaridade"].dropna().unique().tolist())
    esc_sel = st.sidebar.multiselect(
        "5. Grau de Instrução (Escolaridade):",
        options=opcoes_esc,
        default=[],
        placeholder="Todos os níveis de escolaridade",
    )

    # Aplicar filtros ao cubo
    df_filtrado = cubo.copy()
    if regioes_sel:
        df_filtrado = df_filtrado[df_filtrado["regiao_imediata"].isin(regioes_sel)]
    if municipios_sel:
        df_filtrado = df_filtrado[df_filtrado["nome_municipio"].isin(municipios_sel)]
    if setores_sel:
        df_filtrado = df_filtrado[df_filtrado["setor"].isin(setores_sel)]
    if macros_sel:
        df_filtrado = df_filtrado[df_filtrado["macrofamilia"].isin(macros_sel)]
    if esc_sel:
        df_filtrado = df_filtrado[df_filtrado["escolaridade"].isin(esc_sel)]

    if df_filtrado.empty:
        st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
        return

    # =========================================================================
    # CÁLCULO DOS KPIS DO RECORTE ATUAL
    # =========================================================================
    resumo_geral = agregar_recorte(df_filtrado, []).iloc[0]
    por_motivo = agregar_recorte(df_filtrado, ["grupo_movimentacao"]).set_index(
        "grupo_movimentacao"
    )

    # População única dos municípios presentes no filtro territorial
    codigos_mun_no_filtro = df_filtrado["codigo_ibge_7d"].unique()
    populacao_total_recorte = pop_municipios[
        pop_municipios["codigo_ibge_7d"].isin(codigos_mun_no_filtro)
    ]["populacao_estimada_2026"].sum()

    saldo_10k_recorte = (
        (resumo_geral["saldo"] / populacao_total_recorte) * 10000.0
        if populacao_total_recorte > 0
        else 0.0
    )

    sal_adm = (
        por_motivo.loc["1. Admitidos (+1)", "salario_medio"]
        if "1. Admitidos (+1)" in por_motivo.index
        else 0.0
    )
    sal_ped40 = (
        por_motivo.loc["2. Pedido de Demissão (Cód 40)", "salario_medio"]
        if "2. Pedido de Demissão (Cód 40)" in por_motivo.index
        else 0.0
    )
    sal_emp31 = (
        por_motivo.loc["3. Demissão pela Empresa (Cód 31)", "salario_medio"]
        if "3. Demissão pela Empresa (Cód 31)" in por_motivo.index
        else 0.0
    )

    # Banner de contexto do filtro ativo
    descricao_recorte = []
    if regioes_sel:
        descricao_recorte.append(f"**Regiões:** {', '.join(regioes_sel)}")
    if municipios_sel:
        descricao_recorte.append(f"**Municípios:** {', '.join(municipios_sel)}")
    if setores_sel:
        descricao_recorte.append(f"**Setores:** {', '.join(setores_sel)}")
    if macros_sel:
        descricao_recorte.append(f"**Macrofamílias:** {', '.join(macros_sel)}")
    if esc_sel:
        descricao_recorte.append(f"**Escolaridade:** {', '.join(esc_sel)}")

    texto_filtro = (
        " | ".join(descricao_recorte)
        if descricao_recorte
        else "**Estado Completo de Santa Catarina (295 municípios | Indústria Seções B a F)**"
    )
    st.info(f"📌 **Recorte Ativo:** {texto_filtro}")

    # Cartões de KPIs Executivos
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(
        "Saldo Líquido de Vagas",
        f"{int(resumo_geral['saldo']):+,}".replace(",", "."),
        f"{int(resumo_geral['admissoes']):,} adm | {int(resumo_geral['desligamentos']):,} desl".replace(
            ",", "."
        ),
    )
    col2.metric(
        "Saldo por 10.000 Hab.",
        f"{saldo_10k_recorte:+.1f} / 10k",
        f"Pop. recorte: {int(populacao_total_recorte):,}".replace(",", "."),
    )
    col3.metric(
        "Pedidos de Demissão (Cód. 40)",
        f"{resumo_geral['pct_pedido_cod40']:.1f}% das saídas",
        f"{int(resumo_geral['pedido_cod40']):,} trabalhadores saíram".replace(",", "."),
        delta_color="inverse",
    )
    col4.metric(
        "Demissão Empresa (Cód. 31)",
        f"{resumo_geral['pct_empresa_cod31']:.1f}% das saídas",
        f"{int(resumo_geral['empresa_cod31']):,} demitidos s/ justa causa".replace(
            ",", "."
        ),
        delta_color="off",
    )
    col5.metric(
        "Salário: Admitido vs Demitido (31)",
        f"R$ {sal_adm:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        f"{sal_adm - sal_emp31:+.2f} R$ vs Cód. 31 (R$ {sal_emp31:,.0f})",
    )

    # Caixa de Diagnóstico Automático do Recorte
    with st.expander("💡 **Diagnóstico Automático deste Recorte (Como interpretar os números acima?)**", expanded=True):
        razao_40_31 = resumo_geral["razao_40_sobre_31"]
        if resumo_geral["pct_pedido_cod40"] >= 50.0:
            tipo_gargalo = (
                f"**Forte Gargalo de Retenção Voluntária (Cód. 40 = {resumo_geral['pct_pedido_cod40']:.1f}% das saídas, ou {razao_40_31:.1f}x mais pedidos de conta do que demissões pela empresa)**: "
                f"os trabalhadores estão deixando as vagas por conta própria, com salário médio de saída a pedido em **R$ {sal_ped40:,.2f}**."
            )
        elif resumo_geral["pct_empresa_cod31"] > resumo_geral["pct_pedido_cod40"]:
            tipo_gargalo = (
                f"**Predomínio de Desligamento por Iniciativa da Empresa (Cód. 31 = {resumo_geral['pct_empresa_cod31']:.1f}% vs Cód. 40 = {resumo_geral['pct_pedido_cod40']:.1f}%)**: "
                f"neste recorte, as empresas demitiram mais do que os funcionários pediram conta (comum em fim de obras de infraestrutura, reestruturação ou substituição de profissionais com salário médio de **R$ {sal_emp31:,.2f}** por novos a **R$ {sal_adm:,.2f}**)."
            )
        else:
            tipo_gargalo = (
                f"**Pressão Mista de Rotatividade (Pedidos Cód. 40 = {resumo_geral['pct_pedido_cod40']:.1f}% | Empresa Cód. 31 = {resumo_geral['pct_empresa_cod31']:.1f}%)**: "
                f"há tanto evasão voluntária (salário médio de **R$ {sal_ped40:,.2f}**) quanto substituição pela empresa (demitidos ganhavam **R$ {sal_emp31:,.2f}** vs admitidos a **R$ {sal_adm:,.2f}**)."
            )
        st.markdown(f"- {tipo_gargalo}")

    # =========================================================================
    # ABAS DOS 3 EIXOS + TABELA EXPLORADORA
    # =========================================================================
    aba1, aba2, aba3, aba4 = st.tabs(
        [
            "🗺️ Eixo 1: Municípios e Regiões",
            "🏭 Eixo 1 & 2: Setores Industriais (CNAE)",
            "💰 Eixo 2: Mudança de Paradigma (Salário e Escolaridade)",
            "👷 Eixo 3: Profissões e Macrofamílias (CBO IA)",
        ]
    )

    # -------------------------------------------------------------------------
    # ABA 1: EIXO TERRITORIAL (MUNICÍPIOS E REGIÕES)
    # -------------------------------------------------------------------------
    with aba1:
        st.subheader("Distribuição Territorial por Município e Região Imediata")

        df_mun_recorte = agregar_recorte(
            df_filtrado,
            ["regiao_imediata", "codigo_ibge_7d", "nome_municipio", "populacao_estimada_2026"],
        )
        df_mun_recorte["saldo_por_10k_hab"] = (
            df_mun_recorte["saldo"] / df_mun_recorte["populacao_estimada_2026"]
        ) * 10000.0

        col_ctrl1, col_ctrl2 = st.columns([2, 1])
        with col_ctrl1:
            metrica_mun = st.radio(
                "Ordenar gráfico de municípios por:",
                options=[
                    "Saldo Absoluto de Vagas",
                    "Saldo por 10.000 Habitantes (Pop >= 10 mil)",
                    "Maior % de Pedidos de Demissão (Cód. 40)",
                    "Maior Retração (Saldo Negativo)",
                ],
                horizontal=True,
            )
        with col_ctrl2:
            qtd_mun_mostrar = st.slider("Quantidade de municípios no gráfico:", 5, 25, 12)

        if metrica_mun == "Saldo Absoluto de Vagas":
            df_plot_mun = df_mun_recorte.nlargest(qtd_mun_mostrar, "saldo").sort_values(
                "saldo", ascending=True
            )
            col_x_mun = "saldo"
            titulo_mun = f"Top {qtd_mun_mostrar} Municípios — Maior Saldo Líquido de Vagas"
        elif metrica_mun == "Saldo por 10.000 Habitantes (Pop >= 10 mil)":
            eleg_pop = df_mun_recorte[df_mun_recorte["populacao_estimada_2026"] >= 10000]
            if eleg_pop.empty:
                eleg_pop = df_mun_recorte
            df_plot_mun = eleg_pop.nlargest(
                qtd_mun_mostrar, "saldo_por_10k_hab"
            ).sort_values("saldo_por_10k_hab", ascending=True)
            col_x_mun = "saldo_por_10k_hab"
            titulo_mun = f"Top {qtd_mun_mostrar} Municípios — Expansão Acelerada (Saldo por 10 mil hab)"
        elif metrica_mun == "Maior % de Pedidos de Demissão (Cód. 40)":
            eleg_mov = df_mun_recorte[df_mun_recorte["desligamentos"] >= 50]
            if eleg_mov.empty:
                eleg_mov = df_mun_recorte
            df_plot_mun = eleg_mov.nlargest(
                qtd_mun_mostrar, "pct_pedido_cod40"
            ).sort_values("pct_pedido_cod40", ascending=True)
            col_x_mun = "pct_pedido_cod40"
            titulo_mun = f"Top {qtd_mun_mostrar} Municípios — Maior Taxa de Pedido de Demissão (Cód. 40)"
        else:
            df_plot_mun = df_mun_recorte.nsmallest(qtd_mun_mostrar, "saldo").sort_values(
                "saldo", ascending=False
            )
            col_x_mun = "saldo"
            titulo_mun = f"Top {qtd_mun_mostrar} Municípios — Maior Retração de Vagas"

        col_graf_mun, col_reg_mun = st.columns([3, 2])
        with col_graf_mun:
            fig_mun = px.bar(
                df_plot_mun,
                x=col_x_mun,
                y="nome_municipio",
                color="pct_pedido_cod40",
                color_continuous_scale="OrRd",
                orientation="h",
                title=titulo_mun,
                hover_data=[
                    "regiao_imediata",
                    "populacao_estimada_2026",
                    "admissoes",
                    "desligamentos",
                    "saldo",
                    "saldo_por_10k_hab",
                    "pct_pedido_cod40",
                    "pct_empresa_cod31",
                    "salario_medio",
                ],
                labels={
                    "nome_municipio": "Município",
                    "saldo": "Saldo de Vagas",
                    "saldo_por_10k_hab": "Saldo / 10k hab",
                    "pct_pedido_cod40": "% Pedido Cód. 40",
                },
            )
            fig_mun.update_layout(height=480)
            st.plotly_chart(fig_mun, use_container_width=True)

        with col_reg_mun:
            df_reg = agregar_recorte(df_filtrado, ["regiao_imediata"]).sort_values(
                "saldo", ascending=True
            )
            fig_reg = px.bar(
                df_reg,
                x="saldo",
                y="regiao_imediata",
                color="saldo",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                orientation="h",
                title="Saldo por Região Geográfica Imediata (IBGE)",
                hover_data=[
                    "admissoes",
                    "desligamentos",
                    "pct_pedido_cod40",
                    "pct_empresa_cod31",
                    "salario_medio",
                ],
            )
            fig_reg.update_layout(height=480)
            st.plotly_chart(fig_reg, use_container_width=True)

        st.markdown("#### 📋 Tabela Completa de Municípios no Recorte (Pesquisável e Ordenável)")
        st.dataframe(
            df_mun_recorte.sort_values("movimentacoes", ascending=False)[
                [
                    "nome_municipio",
                    "regiao_imediata",
                    "populacao_estimada_2026",
                    "admissoes",
                    "desligamentos",
                    "saldo",
                    "saldo_por_10k_hab",
                    "pct_pedido_cod40",
                    "pct_empresa_cod31",
                    "pct_contrato_cod43_45",
                    "salario_medio",
                ]
            ].rename(
                columns={
                    "nome_municipio": "Município",
                    "regiao_imediata": "Região Imediata",
                    "populacao_estimada_2026": "População (2026)",
                    "admissoes": "Admissões",
                    "desligamentos": "Desligamentos",
                    "saldo": "Saldo Líquido",
                    "saldo_por_10k_hab": "Saldo / 10k Hab",
                    "pct_pedido_cod40": "% Pedido (Cód 40)",
                    "pct_empresa_cod31": "% Empresa (Cód 31)",
                    "pct_contrato_cod43_45": "% Fim Contrato (43/45)",
                    "salario_medio": "Salário Médio (R$)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # -------------------------------------------------------------------------
    # ABA 2: SETORES INDUSTRIAIS (CNAE) E MOTIVOS DE SAÍDA
    # -------------------------------------------------------------------------
    with aba2:
        st.subheader("Desempenho dos Setores Industriais (Divisões CNAE) e Motivos de Desligamento")
        df_setor = agregar_recorte(df_filtrado, ["secao", "cnae_divisao", "setor"])

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            top_setores_saldo = pd.concat(
                [
                    df_setor.nlargest(7, "saldo"),
                    df_setor.nsmallest(7, "saldo"),
                ]
            ).drop_duplicates("cnae_divisao").sort_values("saldo", ascending=True)

            fig_setor_saldo = px.bar(
                top_setores_saldo,
                x="saldo",
                y="setor",
                color="saldo",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                orientation="h",
                title="Setores em Maior Expansão vs. Maior Retração no Recorte",
                hover_data=["admissoes", "desligamentos", "pct_pedido_cod40", "salario_medio"],
            )
            fig_setor_saldo.update_layout(height=500)
            st.plotly_chart(fig_setor_saldo, use_container_width=True)

        with col_s2:
            top_setores_desl = df_setor.nlargest(12, "desligamentos").sort_values(
                "desligamentos", ascending=True
            )
            fig_motivos_setor = go.Figure()
            fig_motivos_setor.add_trace(
                go.Bar(
                    y=top_setores_desl["setor"].str.slice(0, 45),
                    x=top_setores_desl["pedido_cod40"],
                    name="Pedido de Demissão (Cód. 40 - Trabalhador)",
                    orientation="h",
                    marker_color="#e67e22",
                )
            )
            fig_motivos_setor.add_trace(
                go.Bar(
                    y=top_setores_desl["setor"].str.slice(0, 45),
                    x=top_setores_desl["empresa_cod31"],
                    name="Demissão Empresa (Cód. 31 - Sem Justa Causa)",
                    orientation="h",
                    marker_color="#c0392b",
                )
            )
            fig_motivos_setor.add_trace(
                go.Bar(
                    y=top_setores_desl["setor"].str.slice(0, 45),
                    x=top_setores_desl["contrato_cod43_45"],
                    name="Fim de Contrato (Cód. 43/45)",
                    orientation="h",
                    marker_color="#7f8c8d",
                )
            )
            fig_motivos_setor.update_layout(
                barmode="stack",
                title="Composição das Saídas por Setor (Quem pede conta vs. Quem é demitido)",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25),
            )
            st.plotly_chart(fig_motivos_setor, use_container_width=True)

        st.markdown("#### 📋 Tabela Detalhada de Todos os Setores Industriais no Recorte")
        st.dataframe(
            df_setor.sort_values("movimentacoes", ascending=False)[
                [
                    "secao",
                    "cnae_divisao",
                    "setor",
                    "admissoes",
                    "desligamentos",
                    "saldo",
                    "pedido_cod40",
                    "pct_pedido_cod40",
                    "empresa_cod31",
                    "pct_empresa_cod31",
                    "razao_40_sobre_31",
                    "salario_medio",
                ]
            ].rename(
                columns={
                    "secao": "Seção",
                    "cnae_divisao": "CNAE",
                    "setor": "Setor Industrial",
                    "admissoes": "Admissões",
                    "desligamentos": "Desligamentos",
                    "saldo": "Saldo",
                    "pedido_cod40": "Pedidos (40)",
                    "pct_pedido_cod40": "% Pedido (40)",
                    "empresa_cod31": "Demitidos (31)",
                    "pct_empresa_cod31": "% Empresa (31)",
                    "razao_40_sobre_31": "Razão 40/31",
                    "salario_medio": "Salário Médio (R$)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # -------------------------------------------------------------------------
    # ABA 3: EIXO 2 — MUDANÇA DE PARADIGMA (SALÁRIO E ESCOLARIDADE POR MOTIVO)
    # -------------------------------------------------------------------------
    with aba3:
        st.subheader(
            "Comparação de Paradigma: Visão Tradicional vs. Abertura por Tipo de Movimentação (40, 31, 43/45)"
        )
        st.markdown(
            "Veja abaixo como a separação pelo motivo do desligamento revela a **substituição salarial (`Cód. 31`)** e a **baixa retenção (`Cód. 40`)** no recorte filtrado:"
        )

        # Preparar dados da visão tradicional vs visão detalhada
        total_adm_mov = resumo_geral["admissoes"]
        total_desl_mov = resumo_geral["desligamentos"]
        df_desl_apenas = df_filtrado[
            df_filtrado["grupo_movimentacao"] != "1. Admitidos (+1)"
        ]
        sal_desl_geral = (
            df_desl_apenas["soma_salario"].sum()
            / df_desl_apenas["salarios_validos"].replace(0, float("nan")).sum()
            if not df_desl_apenas.empty
            else 0.0
        )

        df_paradigma_antigo = pd.DataFrame(
            [
                {
                    "Grupo": "Admitidos (+1)",
                    "Movimentações": total_adm_mov,
                    "Salário Médio (R$)": sal_adm,
                },
                {
                    "Grupo": "Desligados (Tudo Misturado)",
                    "Movimentações": total_desl_mov,
                    "Salário Médio (R$)": sal_desl_geral,
                },
            ]
        )

        df_paradigma_novo = agregar_recorte(df_filtrado, ["grupo_movimentacao"]).sort_values(
            "grupo_movimentacao"
        )

        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            fig_antigo = px.bar(
                df_paradigma_antigo,
                x="Grupo",
                y="Salário Médio (R$)",
                color="Grupo",
                text_auto=".2f",
                title="1. Paradigma Antigo (Sem separar motivo)",
                color_discrete_sequence=["#27ae60", "#7f8c8d"],
            )
            fig_antigo.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig_antigo, use_container_width=True)

        with col_p2:
            fig_novo = px.bar(
                df_paradigma_novo,
                x="grupo_movimentacao",
                y="salario_medio",
                color="grupo_movimentacao",
                text_auto=".2f",
                title="2. Nosso Paradigma (Separando Cód. 40, Cód. 31 e Cód. 43/45)",
                hover_data=["movimentacoes", "salarios_validos"],
                labels={
                    "grupo_movimentacao": "Motivo da Movimentação",
                    "salario_medio": "Salário Médio (R$)",
                },
                color_discrete_sequence=[
                    "#27ae60",
                    "#e67e22",
                    "#c0392b",
                    "#95a5a6",
                    "#34495e",
                ],
            )
            fig_novo.update_layout(height=420, showlegend=False)
            st.plotly_chart(fig_novo, use_container_width=True)

        # Gráfico de Escolaridade x Salário Médio aberto por Motivo
        st.markdown("#### 🎓 Salário Médio por Escolaridade e Motivo da Movimentação")
        df_esc_motivo = agregar_recorte(
            df_filtrado, ["escolaridade", "grupo_movimentacao"]
        )
        grupos_principais = [
            "1. Admitidos (+1)",
            "2. Pedido de Demissão (Cód 40)",
            "3. Demissão pela Empresa (Cód 31)",
            "4. Fim de Contrato (Cód 43/45)",
        ]
        df_esc_plot = df_esc_motivo[
            df_esc_motivo["grupo_movimentacao"].isin(grupos_principais)
        ]

        fig_esc = px.bar(
            df_esc_plot,
            x="escolaridade",
            y="salario_medio",
            color="grupo_movimentacao",
            barmode="group",
            title="Remuneração Média por Escolaridade: Quem Entra (+1) vs Quem Pede Conta (40) vs Quem é Demitido (31)",
            hover_data=["movimentacoes", "salarios_validos"],
            labels={
                "escolaridade": "Nível de Escolaridade",
                "salario_medio": "Salário Médio (R$)",
                "grupo_movimentacao": "Grupo de Movimentação",
            },
        )
        fig_esc.update_layout(height=460)
        st.plotly_chart(fig_esc, use_container_width=True)

    # -------------------------------------------------------------------------
    # ABA 4: EIXO 3 — MACROFAMÍLIAS DE CBO (IA)
    # -------------------------------------------------------------------------
    with aba4:
        st.subheader("Gargalos por Macrofamília Ocupacional (Classificação de CBOs via IA)")
        df_macro = agregar_recorte(df_filtrado, ["macrofamilia"]).sort_values(
            "movimentacoes", ascending=False
        )

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_macro_saldo = px.bar(
                df_macro.sort_values("saldo", ascending=True),
                x="saldo",
                y="macrofamilia",
                color="saldo",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                orientation="h",
                title="Saldo Líquido de Vagas por Macrofamília Ocupacional",
                hover_data=["admissoes", "desligamentos", "salario_medio"],
            )
            fig_macro_saldo.update_layout(height=500)
            st.plotly_chart(fig_macro_saldo, use_container_width=True)

        with col_m2:
            df_macro_top = df_macro.head(12).sort_values("desligamentos", ascending=True)
            fig_macro_motivos = go.Figure()
            fig_macro_motivos.add_trace(
                go.Bar(
                    y=df_macro_top["macrofamilia"],
                    x=df_macro_top["pedido_cod40"],
                    name="Pedido de Demissão (Cód. 40)",
                    orientation="h",
                    marker_color="#e67e22",
                )
            )
            fig_macro_motivos.add_trace(
                go.Bar(
                    y=df_macro_top["macrofamilia"],
                    x=df_macro_top["empresa_cod31"],
                    name="Demissão Empresa (Cód. 31)",
                    orientation="h",
                    marker_color="#c0392b",
                )
            )
            fig_macro_motivos.add_trace(
                go.Bar(
                    y=df_macro_top["macrofamilia"],
                    x=df_macro_top["contrato_cod43_45"],
                    name="Fim de Contrato (Cód. 43/45)",
                    orientation="h",
                    marker_color="#7f8c8d",
                )
            )
            fig_macro_motivos.update_layout(
                barmode="stack",
                title="Motivo de Saída por Macrofamília (Onde o trabalhador pede conta vs é demitido)",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25),
            )
            st.plotly_chart(fig_macro_motivos, use_container_width=True)

        st.markdown("#### 📋 Tabela Completa das Macrofamílias no Recorte")
        st.dataframe(
            df_macro[
                [
                    "macrofamilia",
                    "admissoes",
                    "desligamentos",
                    "saldo",
                    "pedido_cod40",
                    "pct_pedido_cod40",
                    "empresa_cod31",
                    "pct_empresa_cod31",
                    "razao_40_sobre_31",
                    "salario_medio",
                ]
            ].rename(
                columns={
                    "macrofamilia": "Macrofamília Ocupacional (IA)",
                    "admissoes": "Admissões",
                    "desligamentos": "Desligamentos",
                    "saldo": "Saldo Líquido",
                    "pedido_cod40": "Pedidos (Cód 40)",
                    "pct_pedido_cod40": "% Pedido (Cód 40)",
                    "empresa_cod31": "Demitidos (Cód 31)",
                    "pct_empresa_cod31": "% Empresa (Cód 31)",
                    "razao_40_sobre_31": "Razão 40/31",
                    "salario_medio": "Salário Médio (R$)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
