import pandas as pd


def realizar_inner_join_caged_municipios(
    df_caged: pd.DataFrame, df_municipios: pd.DataFrame
) -> pd.DataFrame:
    """
    Responsabilidade:
    Realizar o cruzamento relacional (Inner Join) entre a base de movimentações
    do Novo CAGED e a base demográfica de municípios do IBGE, utilizando a chave
    de 6 dígitos do município ('município' no CAGED e 'codigo_municipio_6d' nos Municípios).
    """
    print("1. Garantindo que ambas as chaves de município sejam números inteiros...")
    df_caged["município"] = df_caged["município"].astype(int)
    df_municipios["codigo_municipio_6d"] = df_municipios["codigo_municipio_6d"].astype(
        int
    )

    print("2. Executando o Inner Join entre CAGED e Municípios...")
    df_unificado = pd.merge(
        left=df_caged,
        right=df_municipios,
        left_on="município",
        right_on="codigo_municipio_6d",
        how="inner",
    )

    print(
        f"   -> Inner Join concluído! Total de registros cruzados: {len(df_unificado)}"
    )
    return df_unificado
