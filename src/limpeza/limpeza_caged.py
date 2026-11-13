from pathlib import Path
import pandas as pd


def carregar_e_limpar_caged(caminho_csv: Path) -> pd.DataFrame:
    """
    Responsabilidade:
    1. Carregar o arquivo CSV de movimentações do Novo CAGED.
    2. Remover colunas de índice desnecessárias ('Unnamed: 0.1', 'Unnamed: 0').
    3. Filtrar apenas as seções industriais (de 'B' até 'F').
    4. Converter os valores de salário (que vêm com vírgula) para número decimal (float).
    """
    print("1. Carregando a base do Novo CAGED (isso pode levar alguns segundos)...")
    df_caged = pd.read_csv(caminho_csv, sep=";")
    print(f"   -> Total de linhas carregadas originalmente: {len(df_caged)}")

    # Remover colunas de índice que vieram sujas no CSV, caso existam
    colunas_para_remover = []
    for nome_coluna in df_caged.columns:
        if nome_coluna == "Unnamed: 0.1" or nome_coluna == "Unnamed: 0":
            colunas_para_remover.append(nome_coluna)

    if len(colunas_para_remover) > 0:
        print(f"2. Removendo colunas de índice desnecessárias: {colunas_para_remover}...")
        df_caged = df_caged.drop(columns=colunas_para_remover)

    # Definição oficial do Setor Industrial segundo IBGE/CNI/FIESC (Seções B até F)
    # B = Indústrias Extrativas
    # C = Indústrias de Transformação (inclui Agroindústria, Têxtil, Metalmecânica, Eletroeletrônica)
    # D = Eletricidade e Gás
    # E = Água, Esgoto e Gestão de Resíduos
    # F = Construção
    secoes_industriais = ["B", "C", "D", "E", "F"]

    print(f"3. Filtrando apenas as seções industriais {secoes_industriais}...")
    filtro_industria = df_caged["seção"].isin(secoes_industriais)
    df_caged_industrial = df_caged[filtro_industria].copy()
    print(
        f"   -> Total de linhas após filtro industrial (B a F): {len(df_caged_industrial)}"
    )

    # Tratar a coluna 'salário' trocando vírgula por ponto e convertendo para float
    print("4. Convertendo a coluna 'salário' de texto com vírgula para float...")
    salario_texto = df_caged_industrial["salário"].astype(str)
    salario_com_ponto = salario_texto.str.replace(",", ".", regex=False)
    df_caged_industrial["salário"] = salario_com_ponto.astype(float)

    # Aproveitamos para aplicar a mesma limpeza em 'valorsaláriofixo' e 'horascontratuais'
    print("5. Convertendo 'valorsaláriofixo' e 'horascontratuais' para float...")
    valor_fixo_texto = df_caged_industrial["valorsaláriofixo"].astype(str)
    valor_fixo_com_ponto = valor_fixo_texto.str.replace(",", ".", regex=False)
    df_caged_industrial["valorsaláriofixo"] = pd.to_numeric(
        valor_fixo_com_ponto, errors="coerce"
    )

    horas_texto = df_caged_industrial["horascontratuais"].astype(str)
    horas_com_ponto = horas_texto.str.replace(",", ".", regex=False)
    df_caged_industrial["horascontratuais"] = pd.to_numeric(
        horas_com_ponto, errors="coerce"
    )

    print("   -> Base do CAGED industrial limpa com sucesso!")
    return df_caged_industrial
