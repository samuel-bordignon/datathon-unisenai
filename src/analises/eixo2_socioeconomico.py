"""
Eixo 2: Análise Socioeconômica — Escolaridade e Remuneração por Tipo e Motivo de Movimentação.
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from comum import (
    argumentos,
    dados_comuns,
    agregar,
    distribuicao,
    exportar,
    classificar_grupo_movimentacao,
)


def salarios(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Agrega indicadores salariais e de movimentação separando por Admissão vs Desligamento."""
    return agregar(df, chaves + ["tipo_mov"])


def salarios_por_motivo(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """
    Agrega indicadores salariais e de escolaridade separando pelos 5 grupos detalhados
    de movimentação (Admitidos, Pedido Cód. 40, Empresa Cód. 31, Fim Contrato Cód. 43/45).
    """
    df_trab = df
    if "grupo_movimentacao" not in df_trab.columns:
        df_trab = df.copy()
        df_trab["grupo_movimentacao"] = classificar_grupo_movimentacao(df_trab)

    tabela = agregar(df_trab, chaves + ["grupo_movimentacao"])

    if "superior_completo" in df_trab.columns:
        sup = (
            df_trab.groupby(chaves + ["grupo_movimentacao"], dropna=False, observed=True)[
                "superior_completo"
            ]
            .agg(
                quantidade_superior="sum",
                pct_superior_completo=lambda s: s.mean() * 100.0,
            )
            .reset_index()
        )
        tabela = tabela.merge(
            sup, on=chaves + ["grupo_movimentacao"], how="left", validate="one_to_one"
        )

    return tabela


def diferencas(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """
    Calcula as diferenças salariais absolutas (R$) e percentuais (%) entre
    Admitidos e Desligados (usando os Desligados como denominador).
    """
    base = salarios(df, chaves)
    colunas_metricas = ["salario_medio", "salario_mediano", "salarios_validos"]

    admitidos = base[base["tipo_mov"] == "Admissão"][chaves + colunas_metricas].rename(
        columns={
            "salario_medio": "media_admitidos",
            "salario_mediano": "mediana_admitidos",
            "salarios_validos": "n_admitidos_validos",
        }
    )

    desligados = base[base["tipo_mov"] == "Desligamento"][chaves + colunas_metricas].rename(
        columns={
            "salario_medio": "media_desligados",
            "salario_mediano": "mediana_desligados",
            "salarios_validos": "n_desligados_validos",
        }
    )

    resultado = admitidos.merge(
        desligados, on=chaves, how="outer", validate="one_to_one"
    )

    for medida in ["media", "mediana"]:
        col_adm = f"{medida}_admitidos"
        col_des = f"{medida}_desligados"
        col_dif_reais = f"diferenca_{medida}_reais"
        col_dif_pct = f"diferenca_{medida}_pct_desligados"

        resultado[col_dif_reais] = resultado[col_adm] - resultado[col_des]
        denominador_valido = resultado[col_des].where(resultado[col_des] != 0)
        resultado[col_dif_pct] = (resultado[col_dif_reais] / denominador_valido) * 100.0

    resultado["amostra_suficiente"] = (resultado["n_admitidos_validos"] >= 30) & (
        resultado["n_desligados_validos"] >= 30
    )

    # Se a coluna tipo_movimentacao existir, calcular também a diferença específica contra
    # Pedido de Demissão (Cód. 40) e Demissão pela Empresa (Cód. 31)
    if "grupo_movimentacao" in df.columns or "tipo_movimentacao" in df.columns:
        por_motivo = salarios_por_motivo(df, chaves)
        pedido_40 = por_motivo[
            por_motivo["grupo_movimentacao"] == "2. Pedido de Demissão (Cód 40)"
        ][chaves + ["salario_medio", "salario_mediano"]].rename(
            columns={
                "salario_medio": "media_pedido_cod40",
                "salario_mediano": "mediana_pedido_cod40",
            }
        )
        empresa_31 = por_motivo[
            por_motivo["grupo_movimentacao"] == "3. Demissão pela Empresa (Cód 31)"
        ][chaves + ["salario_medio", "salario_mediano"]].rename(
            columns={
                "salario_medio": "media_demitido_empresa_cod31",
                "salario_mediano": "mediana_demitido_empresa_cod31",
            }
        )
        resultado = resultado.merge(pedido_40, on=chaves, how="left")
        resultado = resultado.merge(empresa_31, on=chaves, how="left")
        resultado["diferenca_adm_menos_empresa_cod31_reais"] = (
            resultado["media_admitidos"] - resultado["media_demitido_empresa_cod31"]
        )
        resultado["diferenca_adm_menos_pedido_cod40_reais"] = (
            resultado["media_admitidos"] - resultado["media_pedido_cod40"]
        )

    return resultado


def grafico_escolaridade(tabela: pd.DataFrame, caminho_imagem: Path) -> None:
    """Plota a distribuição percentual de escolaridade entre Admitidos e Desligados."""
    dados = tabela.pivot_table(
        index="escolaridade",
        columns="tipo_mov",
        values="percentual_grupo_tipo_mov",
        aggfunc="sum",
        fill_value=0,
    )
    eixo = dados.plot.barh(figsize=(11, 7))
    eixo.set_xlabel("% dentro do tipo de movimentação")
    eixo.set_ylabel("Escolaridade observada")
    eixo.set_title("Escolaridade de Admitidos e Desligados", fontweight="bold")

    for container, tipo in zip(eixo.containers, dados.columns):
        contagem = (
            tabela[tabela["tipo_mov"] == tipo]
            .set_index("escolaridade")["quantidade"]
            .reindex(dados.index, fill_value=0)
        )
        rotulos = [
            f"{pct:.1f}% (n={int(n):,})" for pct, n in zip(dados[tipo], contagem)
        ]
        eixo.bar_label(container, labels=rotulos, fontsize=6, padding=2)

    eixo.margins(x=0.3)
    eixo.figure.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(eixo.figure)


def grafico_salario(tabela: pd.DataFrame, caminho_imagem: Path) -> None:
    """Plota salário médio e mediano na visão geral (Admissão vs Desligamento)."""
    dados = tabela.set_index("tipo_mov")
    figura, eixo = plt.subplots(figsize=(8, 5))
    barras_plot = eixo.bar(dados.index, dados["salario_medio"], label="Média", color="#2980b9")
    eixo.scatter(
        dados.index,
        dados["salario_mediano"],
        marker="D",
        color="black",
        label="Mediana",
        zorder=3,
    )

    for barra, (_, linha) in zip(barras_plot, dados.iterrows()):
        pos_x = barra.get_x() + (barra.get_width() / 2.0)
        pos_y = barra.get_height()
        texto = (
            f"R$ {linha['salario_medio']:.2f}\n"
            f"n={int(linha['salarios_validos']):,} ({linha['pct_salarios_validos_movimentacoes_grupo']:.1f}%)"
        )
        eixo.text(pos_x, pos_y, texto, ha="center", va="bottom", fontsize=8)

    eixo.set_title("Salário Mensal Nominal e Cobertura (Visão Geral)", fontweight="bold")
    eixo.set_ylabel("R$")
    eixo.legend()
    eixo.margins(y=0.25)
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_salario_por_motivo(
    tabela_geral: pd.DataFrame,
    tabela_motivo: pd.DataFrame,
    caminho_imagem: Path,
) -> None:
    """
    Compara lado a lado a Visão Geral (Admissão vs Desligamento Agregado) com a
    Visão Detalhada por Tipo de Movimentação (Admitidos vs Pedido Cód. 40 vs
    Demissão Empresa Cód. 31 vs Fim de Contrato Cód. 43/45).
    """
    figura, eixos = plt.subplots(1, 2, figsize=(15, 6), sharey=True)

    # Painel Esquerdo: Visão sem separar tipomovimentação
    dados_esq = tabela_geral.set_index("tipo_mov")
    barras_esq = eixos[0].bar(
        dados_esq.index,
        dados_esq["salario_medio"],
        color=["#27ae60", "#7f8c8d"],
        label="Média Salarial (R$)",
    )
    eixos[0].scatter(
        dados_esq.index,
        dados_esq["salario_mediano"],
        marker="D",
        color="black",
        s=50,
        zorder=3,
        label="Mediana (R$)",
    )
    for barra, (_, linha) in zip(barras_esq, dados_esq.iterrows()):
        eixos[0].text(
            barra.get_x() + barra.get_width() / 2.0,
            barra.get_height() + 40,
            f"Média: R$ {linha['salario_medio']:.2f}\nMediana: R$ {linha['salario_mediano']:.2f}\n(n={int(linha['movimentacoes']):,})",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    eixos[0].set_title(
        "Visão Tradicional (Sem separar Tipo de Movimentação)\nDiferença aparente: apenas -R$ 162,67",
        fontsize=10,
        fontweight="bold",
    )
    eixos[0].set_ylabel("Salário Mensal Nominal (R$)")
    eixos[0].legend(loc="upper left")

    # Painel Direito: Visão abrindo por Código 40, 31 e 43/45
    ordem_grupos = [
        "1. Admitidos (+1)",
        "2. Pedido de Demissão (Cód 40)",
        "3. Demissão pela Empresa (Cód 31)",
        "4. Fim de Contrato (Cód 43/45)",
    ]
    dados_dir = (
        tabela_motivo[tabela_motivo["grupo_movimentacao"].isin(ordem_grupos)]
        .set_index("grupo_movimentacao")
        .reindex(ordem_grupos)
    )
    cores_dir = ["#27ae60", "#e67e22", "#c0392b", "#95a5a6"]
    barras_dir = eixos[1].bar(
        range(len(dados_dir)),
        dados_dir["salario_medio"],
        color=cores_dir,
        label="Média Salarial (R$)",
    )
    eixos[1].scatter(
        range(len(dados_dir)),
        dados_dir["salario_mediano"],
        marker="D",
        color="black",
        s=50,
        zorder=3,
        label="Mediana (R$)",
    )
    eixos[1].set_xticks(range(len(dados_dir)))
    eixos[1].set_xticklabels(
        [
            "Admitidos\n(+1)",
            "Pedido Demissão\n(Cód. 40 - Trabalhador)",
            "Demitido Empresa\n(Cód. 31 - Sem Justa Causa)",
            "Fim de Contrato\n(Cód. 43/45 - Temporário)",
        ],
        fontsize=8,
    )

    for barra, (_, linha) in zip(barras_dir, dados_dir.iterrows()):
        eixos[1].text(
            barra.get_x() + barra.get_width() / 2.0,
            barra.get_height() + 40,
            f"Média: R$ {linha['salario_medio']:.2f}\nMediana: R$ {linha['salario_mediano']:.2f}\n(n={int(linha['movimentacoes']):,})",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    eixos[1].set_title(
        "Visão por Tipo de Movimentação (Códigos 40, 31 e 43/45)\nRevela substituição salarial (-R$ 483 no Cód. 31) e baixa retenção no Cód. 40",
        fontsize=10,
        fontweight="bold",
    )
    eixos[1].margins(y=0.25)

    plt.tight_layout()
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_setor_escolaridade(tabela: pd.DataFrame, caminho_imagem: Path) -> None:
    """Plota mapa de calor da mediana salarial por setor industrial e escolaridade."""
    top_setores = (
        tabela.groupby("setor", dropna=False)["salarios_validos"]
        .sum()
        .nlargest(8)
        .index
    )
    dados = tabela[tabela["setor"].isin(top_setores)].pivot_table(
        index="setor",
        columns="escolaridade",
        values="salario_mediano",
        aggfunc="mean",
    )

    figura, eixo = plt.subplots(figsize=(13, 7))
    imagem = eixo.imshow(dados.fillna(0), aspect="auto", cmap="Blues")
    eixo.set_yticks(range(len(dados.index)), dados.index.str.slice(0, 48))
    eixo.set_xticks(
        range(len(dados.columns)), dados.columns, rotation=45, ha="right"
    )
    eixo.set_title(
        "Mediana Salarial por Setor e Escolaridade (R$; zero indica ausência)",
        fontweight="bold",
    )
    figura.colorbar(imagem, ax=eixo, label="R$")

    for pos_y, nome_setor in enumerate(dados.index):
        for pos_x, nome_esc in enumerate(dados.columns):
            item = tabela[
                (tabela["setor"] == nome_setor) & (tabela["escolaridade"] == nome_esc)
            ]
            if not item.empty and item.iloc[0]["salarios_validos"]:
                registro = item.iloc[0]
                pct_ref = registro["remuneracao_relativa_pct_referencia"]
                if pd.notna(pct_ref):
                    texto_celula = f"{int(registro['salarios_validos'])}\n{pct_ref:.0f}%"
                else:
                    texto_celula = f"{int(registro['salarios_validos'])}\n—"
                eixo.text(
                    pos_x, pos_y, texto_celula, ha="center", va="center", fontsize=5
                )

    eixo.set_xlabel("Em cada célula: número de salários válidos / % da referência estadual")
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_diferencas(tabela: pd.DataFrame, caminho_imagem: Path) -> None:
    """Plota os 10 setores com maior diferença salarial absoluta entre Admitidos e Desligados."""
    dados = tabela[tabela["amostra_suficiente"]].copy()
    indices_maiores = dados["diferenca_media_reais"].abs().nlargest(10).index
    dados = dados.reindex(indices_maiores).sort_values("diferenca_media_reais")

    if dados.empty:
        return

    figura, eixo = plt.subplots(figsize=(12, 7))
    barras_plot = eixo.barh(
        dados["setor"].str.slice(0, 50), dados["diferenca_media_reais"], color="#c0392b"
    )

    for barra, (_, linha) in zip(barras_plot, dados.iterrows()):
        texto = f"{linha['diferenca_media_reais']:+.0f} R$ ({linha['diferenca_media_pct_desligados']:+.1f}%)"
        posicao = (barra.get_width(), barra.get_y() + (barra.get_height() / 2.0))
        eixo.annotate(texto, posicao, fontsize=7, va="center")

    eixo.axvline(0, color="black", linewidth=0.5)
    eixo.set_title("Diferença Salarial Média: Admitidos − Desligados", fontweight="bold")
    eixo.set_xlabel("Reais (R$) e percentual sobre a média dos desligados")
    eixo.margins(x=0.45)
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def analisar(df: pd.DataFrame, pasta_saida: Path) -> dict[str, pd.DataFrame]:
    """Executa todas as agregações e gráficos do Eixo 2 (Socioeconômico)."""
    chaves_setor = ["cnae_divisao", "setor"]
    chaves_municipio = ["codigo_ibge_7d", "nome_municipio"]
    chaves_escolaridade = ["codigo_escolaridade", "escolaridade"]

    geral = salarios(df, [])
    geral_por_motivo = salarios_por_motivo(df, [])
    esc = distribuicao(df, [], "escolaridade")
    esc_por_motivo = distribuicao(df, [], "escolaridade", coluna_movimento="grupo_movimentacao")
    faixa = distribuicao(df, [], "faixa_salarial")
    setor_esc = salarios(df, chaves_setor + chaves_escolaridade)
    ranking_diferencas = diferencas(df, chaves_setor).sort_values("diferenca_media_reais")

    # Avaliação de compressão salarial em setores com alta proporção de Ensino Superior
    admitidos_df = df[df["admissoes"] == 1]
    alto_superior = (
        admitidos_df.groupby(chaves_setor, dropna=False, observed=True)
        .agg(
            admitidos=("admissoes", "sum"),
            superior_completo=("superior_completo", "sum"),
            salarios_validos=("salario_valido", "count"),
            n_admitidos_com_referencia=("salario_relativo_referencia", "count"),
            indice_relativo_mediano=("salario_relativo_referencia", "median"),
        )
        .reset_index()
    )

    admitidos_validos_denom = alto_superior["admitidos"].where(
        alto_superior["admitidos"] != 0
    )
    alto_superior["pct_superior_completo_admitidos_setor"] = (
        alto_superior["superior_completo"] / admitidos_validos_denom
    ) * 100.0
    alto_superior["remuneracao_pct_referencia_estadual"] = (
        alto_superior["indice_relativo_mediano"] * 100.0
    )

    setores_elegiveis = alto_superior[
        (alto_superior["admitidos"] >= 30)
        & (alto_superior["n_admitidos_com_referencia"] >= 30)
    ]
    quartil_superior_educ = setores_elegiveis[
        "pct_superior_completo_admitidos_setor"
    ].quantile(0.75)

    alto_superior["escolaridade_alta_remuneracao_relativa_baixa"] = (
        (alto_superior["admitidos"] >= 30)
        & (alto_superior["n_admitidos_com_referencia"] >= 30)
        & (alto_superior["pct_superior_completo_admitidos_setor"] >= quartil_superior_educ)
        & (alto_superior["indice_relativo_mediano"] < 1.0)
    )

    tabelas = {
        "escolaridade_movimento": esc,
        "escolaridade_grupo_movimentacao": esc_por_motivo,
        "faixa_salarial_movimento": faixa,
        "salarios_movimento": geral,
        "salarios_grupo_movimentacao": geral_por_motivo,
        "salarios_setor_movimento": salarios(df, chaves_setor),
        "salarios_setor_grupo_movimentacao": salarios_por_motivo(df, chaves_setor),
        "salarios_municipio_movimento": salarios(df, chaves_municipio),
        "salarios_escolaridade_movimento": salarios(df, chaves_escolaridade),
        "salarios_escolaridade_grupo_movimentacao": salarios_por_motivo(
            df, chaves_escolaridade
        ),
        "salarios_setor_escolaridade_movimento": setor_esc,
        "escolaridade_setor_movimento": distribuicao(df, chaves_setor, "escolaridade"),
        "diferencas_setor": ranking_diferencas,
        "diferencas_escolaridade": diferencas(df, chaves_escolaridade),
        "setores_escolaridade_remuneracao": alto_superior,
    }

    pasta_eixo2 = pasta_saida / "eixo2_socioeconomico"
    exportar(tabelas, pasta_eixo2)

    grafico_escolaridade(esc, pasta_eixo2 / "escolaridade.png")
    grafico_salario(geral, pasta_eixo2 / "salarios_admitidos_desligados.png")
    grafico_salario_por_motivo(
        geral,
        geral_por_motivo,
        pasta_eixo2 / "salarios_por_motivo_movimentacao.png",
    )
    grafico_setor_escolaridade(
        agregar(df, chaves_setor + chaves_escolaridade),
        pasta_eixo2 / "setor_escolaridade_salario.png",
    )
    grafico_diferencas(
        ranking_diferencas, pasta_eixo2 / "ranking_diferencas_salariais.png"
    )

    return tabelas


def main() -> None:
    args = argumentos()
    df, _ = dados_comuns(args)
    analisar(df, args.saida)


if __name__ == "__main__":
    main()
