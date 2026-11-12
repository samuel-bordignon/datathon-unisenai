"""
Eixo 3: Análise de Qualificação Ocupacional (CBOs e Macrofamílias IA) e Motivos de Saída.
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


def grafico_admissoes_macrofamilia(
    familias: pd.DataFrame, caminho_imagem: Path
) -> None:
    """Plota as 10 macrofamílias ocupacionais com maior volume de admissões."""
    top_familias = familias.nlargest(10, "admissoes").sort_values("admissoes")
    figura, eixo = plt.subplots(figsize=(11, 7))
    barras_plot = eixo.barh(
        top_familias["macrofamilia"], top_familias["admissoes"], color="#1f77b4"
    )

    for barra, (_, linha) in zip(barras_plot, top_familias.iterrows()):
        texto = f"{int(linha['admissoes']):,} ({linha['pct_admissoes_total_sc']:.1f}% SC)"
        posicao = (barra.get_width(), barra.get_y() + (barra.get_height() / 2.0))
        eixo.annotate(texto, posicao, va="center", fontsize=8)

    eixo.margins(x=0.35)
    eixo.set_xlabel("Admissões e percentual das admissões em SC")
    eixo.set_title("Macrofamílias Ocupacionais com Mais Admissões", fontweight="bold")
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_motivos_saida_macrofamilia(
    familias: pd.DataFrame, caminho_imagem: Path
) -> None:
    """
    Compara Pedido de Demissão (Cód. 40) vs Demissão pela Empresa (Cód. 31) vs
    Fim de Contrato (Cód. 43/45) nas 10 principais macrofamílias ocupacionais.
    """
    top_familias = familias.nlargest(10, "desligamentos").sort_values("desligamentos")
    rotulos = top_familias["macrofamilia"]

    figura, eixo = plt.subplots(figsize=(13, 7))
    pedido = top_familias["desligamentos_a_pedido"]
    empresa = top_familias["demissoes_sem_justa_causa"]
    contrato = top_familias["terminos_contrato"]

    eixo.barh(
        rotulos,
        pedido,
        label="Pedido de Demissão (Cód. 40 - Trabalhador saiu)",
        color="#e67e22",
    )
    eixo.barh(
        rotulos,
        empresa,
        left=pedido,
        label="Demissão sem Justa Causa (Cód. 31 - Empresa demitiu)",
        color="#c0392b",
    )
    eixo.barh(
        rotulos,
        contrato,
        left=pedido + empresa,
        label="Fim de Contrato Temporário (Cód. 43/45)",
        color="#7f8c8d",
    )

    for indice, (_, linha) in enumerate(top_familias.iterrows()):
        total_3 = (
            linha["desligamentos_a_pedido"]
            + linha["demissoes_sem_justa_causa"]
            + linha["terminos_contrato"]
        )
        razao = (
            linha["desligamentos_a_pedido"] / linha["demissoes_sem_justa_causa"]
            if linha["demissoes_sem_justa_causa"] > 0
            else 0.0
        )
        eixo.text(
            total_3 + (top_familias["desligamentos"].max() * 0.01),
            indice,
            f"Razão 40/31: {razao:.1f}x | Sal. Médio: R$ {linha['salario_medio']:.0f}",
            va="center",
            fontsize=8,
        )

    eixo.set_xlim(0, top_familias["desligamentos"].max() * 1.32)
    eixo.set_title(
        "Macrofamílias Ocupacionais: Quem Pede Demissão (Cód. 40) vs Demitido pela Empresa (Cód. 31)",
        fontsize=11,
        fontweight="bold",
    )
    eixo.set_xlabel("Quantidade de desligamentos (e razão Pedido Cód. 40 / Empresa Cód. 31)")
    eixo.legend(loc="lower right")
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def analisar(df: pd.DataFrame, pasta_saida: Path) -> dict[str, pd.DataFrame]:
    """Executa todas as agregações e gráficos do Eixo 3 (Qualificação e Macrofamílias CBO)."""
    df_trab = df
    if "grupo_movimentacao" not in df_trab.columns:
        df_trab = df.copy()
        df_trab["grupo_movimentacao"] = classificar_grupo_movimentacao(df_trab)

    cbos = agregar(
        df_trab, ["cbo", "descricao_cbo", "macrofamilia", "funcao_profissional"]
    )
    familias = agregar(df_trab, ["macrofamilia"])
    educ = distribuicao(df_trab, ["macrofamilia"], "escolaridade")

    predominante = (
        educ.sort_values(
            ["macrofamilia", "tipo_mov", "quantidade", "escolaridade"],
            ascending=[True, True, False, True],
        )
        .drop_duplicates(["macrofamilia", "tipo_mov"])
    )

    tabelas = {
        "cbos": cbos.sort_values("movimentacoes", ascending=False),
        "macrofamilias": familias.sort_values("admissoes", ascending=False),
        "macrofamilias_ranking_saldo": familias.sort_values("saldo", ascending=False),
        "escolaridade_macrofamilia": educ,
        "escolaridade_predominante": predominante,
        "salarios_macrofamilia_movimento": agregar(
            df_trab, ["macrofamilia", "tipo_mov"]
        ),
        "salarios_macrofamilia_grupo_movimentacao": agregar(
            df_trab, ["macrofamilia", "grupo_movimentacao"]
        ),
        "macrofamilias_mensal": agregar(df_trab, ["competencia", "macrofamilia"]),
        "ocupacoes_mensal": agregar(
            df_trab, ["competencia", "cbo", "descricao_cbo", "macrofamilia"]
        ),
    }

    pasta_eixo3 = pasta_saida / "eixo3_qualificacao"
    exportar(tabelas, pasta_eixo3)

    grafico_admissoes_macrofamilia(
        familias, pasta_eixo3 / "macrofamilias_admissoes.png"
    )
    grafico_motivos_saida_macrofamilia(
        familias, pasta_eixo3 / "macrofamilias_motivos_saida.png"
    )

    return tabelas


def main() -> None:
    args = argumentos()
    df, _ = dados_comuns(args)
    analisar(df, args.saida)


if __name__ == "__main__":
    main()
