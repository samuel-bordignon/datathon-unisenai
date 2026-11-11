from pathlib import Path
import pandas as pd


def exportar_base_limpa_csv(df_unificado: pd.DataFrame, caminho_saida_csv: Path) -> None:
    """
    Responsabilidade:
    Salvar o DataFrame limpo e unificado em um arquivo .csv para ser consumido
    pelas próximas etapas de cálculo de métricas, enriquecimento com IA e Dashboard,
    evitando a necessidade de reprocessar o arquivo bruto de 3,4 milhões de linhas.
    """
    print(f"1. Salvando a base unificada em: {caminho_saida_csv}...")
    df_unificado.to_csv(caminho_saida_csv, index=False, sep=";", encoding="utf-8")
    print("   -> Arquivo CSV exportado com sucesso!")
