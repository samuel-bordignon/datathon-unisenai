from pathlib import Path
import pandas as pd


def carregar_e_limpar_municipios(caminho_csv: Path) -> pd.DataFrame:
    """
    Responsabilidade:
    1. Carregar o arquivo CSV de municípios de Santa Catarina.
    2. Renomear os cabeçalhos sujos (com [-], [2025], tags HTML <span>) para nomes limpos.
    3. Remover colunas que não serão utilizadas na análise (ex: prefeito, gentílico, coluna vazia).
    4. Extrair os 6 primeiros dígitos do código IBGE para permitir o Inner Join com o CAGED.
    """
    print("1. Carregando a base de municípios...")
    df_municipios = pd.read_csv(caminho_csv)

    # Dicionário explícito mapeando o nome antigo (sujo) para o nome novo (limpo)
    mapa_nomes_colunas = {
        "Município [-]": "nome_municipio",
        "Código [-]": "codigo_ibge_7d",
        "Gentílico [-]": "gentilico",
        "Prefeito [2025]": "prefeito",
        "Área Territorial - km² [2025]": "area_territorial_km2",
        "População no último censo - pessoas [2022]": "populacao_censo_2022",
        "Densidade demográfica - hab/km² [2022]": "densidade_demografica_2022",
        "População estimada - pessoas [2026]": "populacao_estimada_2026",
        "Escolarização <span>6 a 14 anos</span> - % [2022]": "taxa_escolarizacao_2022",
        "IDHM <span>Índice de desenvolvimento humano municipal</span> [2010]": "idhm_2010",
        "Mortalidade infantil - óbitos por mil nascidos vivos [2025]": "mortalidade_infantil_2025",
        "Total de receitas brutas realizadas - R$ [2025]": "receitas_brutas_2025",
        "Total de despesas brutas empenhadas - R$ [2025]": "despesas_brutas_2025",
        "PIB per capita - R$ [2023]": "pib_per_capita_2023",
    }

    print("2. Renomeando cabeçalhos dos municípios para nomes limpos...")
    df_municipios = df_municipios.rename(columns=mapa_nomes_colunas)

    # Lista de colunas que queremos manter para a análise
    colunas_para_manter = [
        "nome_municipio",
        "codigo_ibge_7d",
        "area_territorial_km2",
        "populacao_censo_2022",
        "densidade_demografica_2022",
        "populacao_estimada_2026",
        "taxa_escolarizacao_2022",
        "idhm_2010",
        "pib_per_capita_2023",
    ]

    print("3. Selecionando apenas as colunas relevantes de municípios...")
    df_municipios = df_municipios[colunas_para_manter].copy()

    # Criar a chave de 6 dígitos (cortando o 7º dígito verificador do IBGE)
    # Fazemos passo a passo: converte para texto -> pega os 6 primeiros caracteres -> converte para inteiro
    print("4. Extraindo os 6 primeiros dígitos do código do IBGE para o Inner Join...")
    codigo_como_texto = df_municipios["codigo_ibge_7d"].astype(str)
    codigo_6_digitos_texto = codigo_como_texto.str.slice(0, 6)
    df_municipios["codigo_municipio_6d"] = codigo_6_digitos_texto.astype(int)

    # Garantir que população, IDHM e PIB sejam numéricos
    df_municipios["populacao_censo_2022"] = pd.to_numeric(
        df_municipios["populacao_censo_2022"], errors="coerce"
    )
    df_municipios["populacao_estimada_2026"] = pd.to_numeric(
        df_municipios["populacao_estimada_2026"], errors="coerce"
    )
    df_municipios["pib_per_capita_2023"] = pd.to_numeric(
        df_municipios["pib_per_capita_2023"], errors="coerce"
    )
    df_municipios["idhm_2010"] = pd.to_numeric(
        df_municipios["idhm_2010"], errors="coerce"
    )

    print(
        f"   -> Base de municípios limpa com sucesso! Total de municípios: {len(df_municipios)}"
    )
    return df_municipios
