"""
Eixo 1: Análise Territorial e Setorial das Movimentações Industriais em SC.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from matplotlib.colors import TwoSlopeNorm
import pandas as pd

from comum import argumentos, dados_comuns, agregar, exportar, REFERENCIAS


def mapa(tabela_municipios: pd.DataFrame, caminho_imagem: Path) -> None:
    """
    Gera o mapa coroplético de saldo de empregos industriais nos 295 municípios
    de Santa Catarina usando a malha oficial do IBGE (GeoJSON).
    """
    caminho_geojson = REFERENCIAS / "malha_sc.geojson"
    malha_geo = json.loads(caminho_geojson.read_text(encoding="utf-8"))
    mapa_saldos = tabela_municipios.set_index("codigo_ibge_7d")["saldo"].to_dict()

    poligonos = []
    valores_cor = []

    for feicao in malha_geo["features"]:
        codigo_area = str(feicao["properties"]["codarea"]).zfill(7)
        geometria = feicao["geometry"]
        coordenadas = geometria["coordinates"]

        if geometria["type"] == "Polygon":
            lista_poligonos = [coordenadas]
        else:
            lista_poligonos = coordenadas

        for poligono in lista_poligonos:
            poligonos.append(Polygon(poligono[0], closed=True))
            valores_cor.append(mapa_saldos.get(codigo_area, 0))

    limite_escala = max(abs(min(valores_cor)), abs(max(valores_cor)), 1)

    figura, eixo = plt.subplots(figsize=(11, 8))
    normalizador = TwoSlopeNorm(vmin=-limite_escala, vcenter=0, vmax=limite_escala)
    colecao = PatchCollection(
        poligonos,
        cmap="RdBu",
        norm=normalizador,
        edgecolor="white",
        linewidth=0.15,
    )
    colecao.set_array(valores_cor)
    eixo.add_collection(colecao)
    eixo.autoscale_view()
    eixo.set_aspect("equal")
    eixo.set_title("Saldo de empregos industriais por município (SC)", fontsize=12, fontweight="bold")
    eixo.set_axis_off()

    figura.colorbar(
        colecao,
        ax=eixo,
        label="Saldo (admissões − desligamentos)",
        shrink=0.7,
    )
    figura.savefig(caminho_imagem, dpi=160, bbox_inches="tight")
    plt.close(figura)


def barras(
    tabela: pd.DataFrame,
    coluna_valor: str,
    caminho_imagem: Path,
    titulo: str,
    coluna_percentual: str,
) -> None:
    """Gera gráfico de barras horizontais para os 12 maiores setores industriais."""
    dados = tabela.nlargest(12, coluna_valor).sort_values(coluna_valor)
    figura, eixo = plt.subplots(figsize=(12, 7))

    rotulos_setor = dados["setor"].str.slice(0, 55)
    barras_plot = eixo.barh(rotulos_setor, dados[coluna_valor], color="#1f77b4")
    maior_valor = max(dados[coluna_valor].max(), 1)

    for barra, (_, linha) in zip(barras_plot, dados.iterrows()):
        posicao_x = barra.get_width() + (maior_valor * 0.01)
        posicao_y = barra.get_y() + (barra.get_height() / 2.0)
        texto_barra = f"{int(linha[coluna_valor]):,} ({linha[coluna_percentual]:.1f}% SC)"
        eixo.text(posicao_x, posicao_y, texto_barra, va="center", fontsize=8)

    eixo.set_xlim(0, maior_valor * 1.35)
    eixo.set_title(titulo, fontsize=12, fontweight="bold")
    eixo.set_xlabel("Movimentações e participação no total estadual")
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def grafico_motivos_desligamento_setor(
    tabela_setor: pd.DataFrame, caminho_imagem: Path
) -> None:
    """
    Compara a composição dos desligamentos (Pedido Cód. 40 vs Empresa Cód. 31 vs
    Fim de Contrato Cód. 43/45) nos 10 setores industriais com maior volume de saídas.
    """
    dados = tabela_setor.nlargest(10, "desligamentos").sort_values("desligamentos")
    rotulos = dados["setor"].str.slice(0, 48)

    figura, eixo = plt.subplots(figsize=(13, 7))
    pedido = dados["desligamentos_a_pedido"]
    empresa = dados["demissoes_sem_justa_causa"]
    contrato = dados["terminos_contrato"]

    eixo.barh(rotulos, pedido, label="Pedido de Demissão (Cód. 40 - Trabalhador)", color="#e67e22")
    eixo.barh(
        rotulos,
        empresa,
        left=pedido,
        label="Demissão sem Justa Causa (Cód. 31 - Empresa)",
        color="#c0392b",
    )
    eixo.barh(
        rotulos,
        contrato,
        left=pedido + empresa,
        label="Fim de Contrato Temporário (Cód. 43/45)",
        color="#7f8c8d",
    )

    for indice, (_, linha) in enumerate(dados.iterrows()):
        total_3 = (
            linha["desligamentos_a_pedido"]
            + linha["demissoes_sem_justa_causa"]
            + linha["terminos_contrato"]
        )
        pct_pedido = linha["pct_desligamentos_a_pedido_desligamentos_grupo"]
        pct_emp = linha["pct_demissoes_empresa_desligamentos_grupo"]
        eixo.text(
            total_3 + (dados["desligamentos"].max() * 0.01),
            indice,
            f"40: {pct_pedido:.1f}% | 31: {pct_emp:.1f}%",
            va="center",
            fontsize=8,
        )

    eixo.set_xlim(0, dados["desligamentos"].max() * 1.28)
    eixo.set_title(
        "Composição dos Desligamentos por Setor Industrial (Cód. 40 vs Cód. 31 vs Cód. 43/45)",
        fontsize=11,
        fontweight="bold",
    )
    eixo.set_xlabel("Quantidade de desligamentos (e % sobre total de saídas do setor)")
    eixo.legend(loc="lower right")
    figura.savefig(caminho_imagem, dpi=150, bbox_inches="tight")
    plt.close(figura)


def analisar(df: pd.DataFrame, pasta_saida: Path) -> dict[str, pd.DataFrame]:
    """Executa todas as agregações e gráficos do Eixo 1 (Territorial e Setorial)."""
    chaves_municipio = ["codigo_ibge_7d", "nome_municipio", "populacao_estimada_2026"]
    municipio = agregar(df, chaves_municipio)

    populacao_valida = municipio["populacao_estimada_2026"].where(
        municipio["populacao_estimada_2026"] > 0
    )
    municipio["saldo_por_10000_habitantes"] = (
        municipio["saldo"] / populacao_valida
    ) * 10000.0

    quartil_75 = municipio["saldo_por_10000_habitantes"].quantile(0.75)
    municipio["crescimento_expressivo"] = (municipio["saldo"] > 0) & (
        municipio["saldo_por_10000_habitantes"] >= quartil_75
    )

    setor = agregar(df, ["secao", "cnae_divisao", "setor"])

    tabelas = {
        "municipios": municipio,
        "ranking_municipios": municipio.sort_values("saldo", ascending=False),
        "regioes_imediatas": agregar(df, ["codigo_regiao_imediata", "regiao_imediata"]),
        "secoes": agregar(df, ["secao"]),
        "setores_divisao": setor,
        "subclasses": agregar(
            df, ["secao", "cnae_divisao", "cnae_subclasse", "descricao_subclasse"]
        ),
        "municipio_setor": agregar(
            df, ["codigo_ibge_7d", "nome_municipio", "cnae_divisao", "setor"]
        ),
        "municipios_mensal": agregar(
            df, ["competencia", "codigo_ibge_7d", "nome_municipio"]
        ),
        "regioes_mensal": agregar(
            df, ["competencia", "codigo_regiao_imediata", "regiao_imediata"]
        ),
        "setores_mensal": agregar(
            df, ["competencia", "secao", "cnae_divisao", "setor"]
        ),
    }

    pasta_eixo1 = pasta_saida / "eixo1_territorial"
    exportar(tabelas, pasta_eixo1)

    mapa(municipio, pasta_eixo1 / "mapa_saldo.png")
    barras(
        setor,
        "admissoes",
        pasta_eixo1 / "setores_admissoes.png",
        "Setores Industriais com Mais Admissões",
        "pct_admissoes_total_sc",
    )
    barras(
        setor,
        "desligamentos",
        pasta_eixo1 / "setores_desligamentos.png",
        "Setores Industriais com Mais Desligamentos",
        "pct_desligamentos_total_sc",
    )
    grafico_motivos_desligamento_setor(
        setor, pasta_eixo1 / "setores_motivos_desligamento.png"
    )

    return tabelas


def main() -> None:
    args = argumentos()
    df, _ = dados_comuns(args)
    analisar(df, args.saida)


if __name__ == "__main__":
    main()
