"""
Módulo compartilhado de leitura, validação, enriquecimento e cálculo de métricas
para os três eixos de análise do Novo CAGED Industrial de Santa Catarina.
"""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

# Caminhos principais do projeto
RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / "database" / "doc" / "Caged_Industrial_SC_Limpo_Unificado.csv"
SAIDA = RAIZ / "database" / "resultados"
REFERENCIAS = RAIZ / "database" / "doc" / "referencias_analises"
DICIONARIO = RAIZ / "database" / "doc" / "Dicionario_de_dados.xlsx"
CATALOGO = Path(__file__).with_name("catalogo_cbos_ia.csv")

# Colunas utilizadas nas análises dos 3 Eixos
COLUNAS = [
    "competênciamov",
    "município",
    "seção",
    "subclasse",
    "saldomovimentação",
    "cbo2002ocupação",
    "graudeinstrução",
    "salário",
    "indtrabintermitente",
    "tipomovimentação",
    "nome_municipio",
    "codigo_ibge_7d",
    "populacao_estimada_2026",
    "indicadordeforadoprazo",
]

CODIGOS = {
    "município": "string",
    "subclasse": "string",
    "cbo2002ocupação": "string",
    "codigo_ibge_7d": "string",
}

MINIMOS = {
    2024: 1412.0,
    2025: 1518.0,
    2026: 1621.0,
}


def argumentos():
    """Lê os argumentos de linha de comando com padrões aprovados para o projeto."""
    parser = argparse.ArgumentParser(
        description="Executa as análises do mercado de trabalho industrial de SC."
    )
    parser.add_argument("--entrada", type=Path, default=ENTRADA)
    parser.add_argument("--inicio", type=int, default=202509)
    parser.add_argument("--fim", type=int, default=202608)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    return parser.parse_args()


def hash_arquivo(caminho_arquivo: Path) -> str:
    """Calcula o hash SHA-256 do arquivo de entrada para auditoria de integridade."""
    calculador_hash = hashlib.sha256()
    with open(caminho_arquivo, "rb") as arquivo:
        while True:
            bloco = arquivo.read(1024 * 1024)
            if not bloco:
                break
            calculador_hash.update(bloco)
    return calculador_hash.hexdigest()


def dicionario(nome_aba: str) -> pd.DataFrame:
    """Carrega uma aba do arquivo Excel Dicionario_de_dados.xlsx como tabela (codigo, descricao)."""
    tabela = pd.read_excel(DICIONARIO, sheet_name=nome_aba, dtype=str)
    tabela = tabela.iloc[:, :2].copy()
    tabela.columns = ["codigo", "descricao"]
    tabela = tabela.dropna(subset=["codigo"])
    tabela = tabela.drop_duplicates(subset=["codigo"])
    return tabela


def elegibilidade_salarial(
    salario: pd.Series, minimo: pd.Series, intermitente: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """
    Aplica a regra oficial do MTE para estatísticas salariais:
    - Salário entre 0,3 e 150 salários mínimos vigentes na competência.
    - Trabalhador não intermitente (indtrabintermitente == 0).
    Retorna: (mascara_faixa_valida, mascara_elegivel_final).
    """
    limite_inferior = minimo * 0.3
    limite_superior = minimo * 150.0
    dentro_da_faixa = (salario >= limite_inferior) & (salario <= limite_superior)
    nao_intermitente = intermitente == 0
    elegivel_final = dentro_da_faixa & nao_intermitente
    return dentro_da_faixa, elegivel_final


def classificar_grupo_movimentacao(df: pd.DataFrame) -> pd.Series:
    """
    Classifica cada registro em um dos 5 grupos de movimentação para separar:
    - Contratações (+1)
    - Saídas voluntárias a pedido do trabalhador (Cód. 40 -> Sinal de Retenção/Salário)
    - Demissões por iniciativa da empresa sem justa causa (Cód. 31 -> Sinal de Substituição/Corte)
    - Términos de contrato temporário (Códigos 43 e 45 -> Giro contratual previsto)
    - Outros desligamentos (Justa causa, acordo, aposentadoria, morte, etc.)
    """
    grupo = pd.Series("5. Outros Desligamentos", index=df.index, dtype="string")

    if "saldo_mov" in df.columns:
        eh_admissao = df["saldo_mov"] == 1
        eh_desligamento = df["saldo_mov"] == -1
    else:
        eh_admissao = df["admissoes"] == 1
        eh_desligamento = df["desligamentos"] == 1

    grupo.loc[eh_admissao] = "1. Admitidos (+1)"

    if "tipo_movimentacao" in df.columns:
        tipo_cod = pd.to_numeric(df["tipo_movimentacao"], errors="coerce")
        grupo.loc[eh_desligamento & (tipo_cod == 40)] = "2. Pedido de Demissão (Cód 40)"
        grupo.loc[eh_desligamento & (tipo_cod == 31)] = "3. Demissão pela Empresa (Cód 31)"
        grupo.loc[eh_desligamento & (tipo_cod.isin([43, 45]))] = "4. Fim de Contrato (Cód 43/45)"
    elif "desligamentos_a_pedido" in df.columns:
        grupo.loc[eh_desligamento & (df["desligamentos_a_pedido"] == 1)] = "2. Pedido de Demissão (Cód 40)"

    return grupo


def carregar(args) -> tuple[pd.DataFrame, dict]:
    """
    Carrega a base limpa unificada, executa a auditoria de integridade,
    filtra o período principal e enriquece com dados de escolaridade, CNAE,
    regiões imediatas do IBGE, catálogo de CBOs e grupos de movimentação.
    """
    if args.inicio > args.fim:
        raise ValueError("Competência inicial não pode ser posterior à final.")

    cabecalho = pd.read_csv(args.entrada, sep=";", encoding="utf-8", nrows=0)
    colunas_faltantes = set(COLUNAS) - set(cabecalho.columns)
    if colunas_faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(colunas_faltantes)}")

    # Leitura completa para auditoria das 38 colunas e contabilização de repetições exatas
    completo = pd.read_csv(
        args.entrada, sep=";", encoding="utf-8", dtype=CODIGOS, low_memory=False
    )
    tipos_colunas = completo.dtypes.astype(str).to_dict()
    total_duplicados = int(completo.duplicated().sum())

    competencia = pd.to_numeric(completo["competênciamov"], errors="coerce")
    dentro_do_periodo = competencia.between(args.inicio, args.fim)

    auditoria = {
        "linhas_total": len(completo),
        "linhas_periodo": int(dentro_do_periodo.sum()),
        "linhas_antes_periodo": int((competencia < args.inicio).sum()),
        "linhas_depois_periodo": int((competencia > args.fim).sum()),
        "competencias_invalidas": int(competencia.isna().sum()),
        "repeticoes_identicas_excedentes": total_duplicados,
        "inicio": args.inicio,
        "fim": args.fim,
        "tipos_colunas": tipos_colunas,
        "sha256_entrada": hash_arquivo(args.entrada),
    }

    # Selecionar apenas registros do período e colunas necessárias para liberar memória
    df = completo.loc[dentro_do_periodo, COLUNAS].copy()
    del completo

    if df.empty:
        raise ValueError("Nenhum registro encontrado no período selecionado.")

    secoes_validas = ["B", "C", "D", "E", "F"]
    if not df["seção"].isin(secoes_validas).all():
        raise ValueError("Existem seções não industriais na base de entrada.")

    if not df["saldomovimentação"].isin([-1, 1]).all():
        raise ValueError("Valores inválidos encontrados em saldomovimentação.")

    # Padronizar códigos como texto com zeros à esquerda preservados
    regras_largura_codigo = [
        ("município", 6),
        ("subclasse", 7),
        ("cbo2002ocupação", 6),
        ("codigo_ibge_7d", 7),
    ]
    for nome_coluna, largura in regras_largura_codigo:
        texto_limpo = df[nome_coluna].str.replace(r"\.0$", "", regex=True)
        df[nome_coluna] = texto_limpo.str.zfill(largura)

    # Renomear colunas para nomes padronizados sem acentos
    mapa_renomeacao = {
        "competênciamov": "competencia",
        "município": "codigo_municipio_6d",
        "seção": "secao",
        "subclasse": "cnae_subclasse",
        "saldomovimentação": "saldo_mov",
        "cbo2002ocupação": "cbo",
        "graudeinstrução": "codigo_escolaridade",
        "salário": "salario",
        "tipomovimentação": "tipo_movimentacao",
    }
    df = df.rename(columns=mapa_renomeacao)

    # Validar integridade geográfica de Santa Catarina (código UF 42)
    if not df["codigo_ibge_7d"].str.startswith("42").all():
        raise ValueError("Foram encontrados municípios fora de Santa Catarina.")
    if not (df["codigo_ibge_7d"].str.slice(0, 6) == df["codigo_municipio_6d"]).all():
        raise ValueError("Incompatibilidade entre chave IBGE 7d e chave CAGED 6d.")

    verificacao_demografica = df.groupby("codigo_ibge_7d", dropna=False)[
        ["nome_municipio", "populacao_estimada_2026"]
    ].nunique(dropna=False)
    if (verificacao_demografica > 1).any(axis=None):
        raise ValueError("Dados demográficos divergentes para um mesmo município.")

    # Criar variáveis derivadas de CNAE e de Tipo de Movimentação
    df["cnae_divisao"] = df["cnae_subclasse"].str.slice(0, 2)
    df["admissoes"] = (df["saldo_mov"] == 1).astype("int8")
    df["desligamentos"] = (df["saldo_mov"] == -1).astype("int8")

    # Indicadores específicos por motivo de desligamento (Códigos 40, 31 e 43/45)
    df["desligamentos_a_pedido"] = (
        (df["desligamentos"] == 1) & (df["tipo_movimentacao"] == 40)
    ).astype("int8")
    df["demissoes_sem_justa_causa"] = (
        (df["desligamentos"] == 1) & (df["tipo_movimentacao"] == 31)
    ).astype("int8")
    df["terminos_contrato"] = (
        (df["desligamentos"] == 1) & (df["tipo_movimentacao"].isin([43, 45]))
    ).astype("int8")

    df["tipo_mov"] = df["saldo_mov"].map({1: "Admissão", -1: "Desligamento"})
    df["grupo_movimentacao"] = classificar_grupo_movimentacao(df)

    # Validação e recorte de elegibilidade salarial segundo critério do MTE
    ano_competencia = df["competencia"] // 100
    salario_minimo_vigente = ano_competencia.map(MINIMOS)
    if salario_minimo_vigente.isna().any():
        anos_sem_minimo = sorted(ano_competencia[salario_minimo_vigente.isna()].unique())
        raise ValueError(f"Salário mínimo não configurado para os anos: {anos_sem_minimo}")

    salario_numerico = pd.to_numeric(df["salario"], errors="coerce")
    faixa_ok, elegivel = elegibilidade_salarial(
        salario_numerico, salario_minimo_vigente, df["indtrabintermitente"]
    )
    intermitencia_ok = df["indtrabintermitente"] == 0

    df["salario_valido"] = salario_numerico.where(elegivel)
    df["salario_em_minimos"] = (salario_numerico / salario_minimo_vigente).where(elegivel)

    limites_faixas = [0, 1, 1.5, 2, 3, 5, 10, float("inf")]
    rotulos_faixas = ["Até 1", ">1 a 1,5", ">1,5 a 2", ">2 a 3", ">3 a 5", ">5 a 10", ">10"]
    faixas_categorizadas = pd.cut(
        df["salario_em_minimos"], bins=limites_faixas, labels=rotulos_faixas
    )
    df["faixa_salarial"] = (
        faixas_categorizadas.astype("string").fillna("Inelegível ou ausente")
    )

    auditoria["salarios"] = {
        "validos": int(elegivel.sum()),
        "ausentes": int(salario_numerico.isna().sum()),
        "fora_faixa_nao_ausente": int((salario_numerico.notna() & (~faixa_ok)).sum()),
        "intermitentes_ou_desconhecidos": int((~intermitencia_ok).sum()),
        "exclusoes_unicas": int((~elegivel).sum()),
    }

    auditoria["motivos_desligamento"] = {
        "total_desligamentos": int(df["desligamentos"].sum()),
        "pedido_demissao_cod40": int(df["desligamentos_a_pedido"].sum()),
        "demissao_sem_justa_causa_cod31": int(df["demissoes_sem_justa_causa"].sum()),
        "termino_contrato_cod43_45": int(df["terminos_contrato"].sum()),
    }

    # Enriquecimento 1: Escolaridade (Dicionário de Dados)
    tabela_escolaridade = dicionario("graudeinstrução").rename(
        columns={"codigo": "codigo_escolaridade", "descricao": "escolaridade"}
    )
    df["codigo_escolaridade"] = (
        df["codigo_escolaridade"].astype("string").str.replace(r"\.0$", "", regex=True)
    )
    df = df.merge(
        tabela_escolaridade, on="codigo_escolaridade", how="left", validate="many_to_one"
    )
    df["escolaridade"] = df["escolaridade"].fillna("Não identificado")
    df["superior_completo"] = (
        df["codigo_escolaridade"].isin(["9", "10", "11", "80"]).astype("int8")
    )

    # Enriquecimento 2: Regiões Geográficas Imediatas (IBGE)
    caminho_mun_json = REFERENCIAS / "municipios.json"
    dados_mun_ibge = json.loads(caminho_mun_json.read_text(encoding="utf-8"))
    tabela_mun_ibge = pd.json_normalize(dados_mun_ibge)
    tabela_mun_ibge = tabela_mun_ibge[
        ["id", "regiao-imediata.id", "regiao-imediata.nome"]
    ].rename(
        columns={
            "id": "codigo_ibge_7d",
            "regiao-imediata.id": "codigo_regiao_imediata",
            "regiao-imediata.nome": "regiao_imediata",
        }
    )
    tabela_mun_ibge["codigo_ibge_7d"] = (
        tabela_mun_ibge["codigo_ibge_7d"].astype("string").str.zfill(7)
    )
    df = df.merge(tabela_mun_ibge, on="codigo_ibge_7d", how="left", validate="many_to_one")

    # Enriquecimento 3: Divisões e Subclasses CNAE
    tabela_divisao = pd.read_json(REFERENCIAS / "cnae_divisoes.json", dtype={"id": str})
    tabela_divisao = tabela_divisao[["id", "descricao"]].rename(
        columns={"id": "cnae_divisao", "descricao": "setor"}
    )
    tabela_divisao["cnae_divisao"] = (
        tabela_divisao["cnae_divisao"].astype("string").str.zfill(2)
    )
    df = df.merge(tabela_divisao, on="cnae_divisao", how="left", validate="many_to_one")

    tabela_subclasse = dicionario("subclasse").rename(
        columns={"codigo": "cnae_subclasse", "descricao": "descricao_subclasse"}
    )
    tabela_subclasse["cnae_subclasse"] = tabela_subclasse["cnae_subclasse"].str.zfill(7)
    df = df.merge(
        tabela_subclasse, on="cnae_subclasse", how="left", validate="many_to_one"
    )

    # Enriquecimento 4: Catálogo de CBOs e Macrofamílias (IA)
    tabela_catalogo_cbo = pd.read_csv(
        CATALOGO, sep=";", dtype={"cbo": "string"}, encoding="utf-8-sig"
    )
    if tabela_catalogo_cbo["cbo"].duplicated().any():
        raise ValueError("Existem códigos CBO duplicados no catálogo de classificação.")

    df = df.merge(tabela_catalogo_cbo, on="cbo", how="left", validate="many_to_one")
    for coluna_cat in ["macrofamilia", "funcao_profissional", "descricao_cbo", "justificativa"]:
        valor_padrao = (
            "Descrição não identificada"
            if coluna_cat == "descricao_cbo"
            else "Pendente de classificação"
        )
        df[coluna_cat] = df[coluna_cat].fillna(valor_padrao)

    auditoria["referencias"] = {
        "municipios_sem_regiao": int(df["regiao_imediata"].isna().sum()),
        "movimentacoes_cbo_pendente": int(
            (df["macrofamilia"] == "Pendente de classificação").sum()
        ),
    }

    # Cálculo da mediana estadual de referência por competência e escolaridade (entre admitidos)
    mascara_adm_valido = (df["admissoes"] == 1) & df["salario_valido"].notna()
    referencia_estadual = (
        df.loc[mascara_adm_valido]
        .groupby(["competencia", "codigo_escolaridade"], dropna=False, observed=True)[
            "salario_valido"
        ]
        .agg(
            mediana_estadual_escolaridade_mes="median",
            n_referencia_estadual="count",
        )
        .reset_index()
    )
    df = df.merge(
        referencia_estadual,
        on=["competencia", "codigo_escolaridade"],
        how="left",
        validate="many_to_one",
    )

    condicao_referencia_valida = (
        mascara_adm_valido
        & (df["mediana_estadual_escolaridade_mes"] > 0)
        & (df["n_referencia_estadual"] >= 30)
    )
    df["salario_relativo_referencia"] = (
        df["salario_valido"] / df["mediana_estadual_escolaridade_mes"]
    ).where(condicao_referencia_valida)

    return df, auditoria


def agregar(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """
    Agrega o DataFrame pelas chaves informadas calculando contagens de movimentação,
    desligamentos por motivo (40, 31, 43/45), estatísticas salariais (média, mediana,
    desvio padrão) e participações relativas com denominadores explícitos.
    """
    # Garantir compatibilidade caso um DataFrame sintético de teste não possua as novas colunas
    df_trab = df
    precisa_copia = False
    for col_motivo in ["demissoes_sem_justa_causa", "terminos_contrato"]:
        if col_motivo not in df_trab.columns:
            if not precisa_copia:
                df_trab = df.copy()
                precisa_copia = True
            df_trab[col_motivo] = 0

    if chaves:
        agrupador = df_trab.groupby(chaves, dropna=False, observed=True)
        out = agrupador.agg(
            admissoes=("admissoes", "sum"),
            desligamentos=("desligamentos", "sum"),
            desligamentos_a_pedido=("desligamentos_a_pedido", "sum"),
            demissoes_sem_justa_causa=("demissoes_sem_justa_causa", "sum"),
            terminos_contrato=("terminos_contrato", "sum"),
            salarios_validos=("salario_valido", "count"),
            salario_medio=("salario_valido", "mean"),
            salario_mediano=("salario_valido", "median"),
            salario_desvio_padrao=("salario_valido", "std"),
            remuneracao_relativa_mediana=("salario_relativo_referencia", "median"),
            n_admitidos_com_referencia=("salario_relativo_referencia", "count"),
        ).reset_index()
    else:
        out = pd.DataFrame(
            [
                {
                    "admissoes": df_trab["admissoes"].sum(),
                    "desligamentos": df_trab["desligamentos"].sum(),
                    "desligamentos_a_pedido": df_trab["desligamentos_a_pedido"].sum(),
                    "demissoes_sem_justa_causa": df_trab["demissoes_sem_justa_causa"].sum(),
                    "terminos_contrato": df_trab["terminos_contrato"].sum(),
                    "salarios_validos": df_trab["salario_valido"].count(),
                    "salario_medio": df_trab["salario_valido"].mean(),
                    "salario_mediano": df_trab["salario_valido"].median(),
                    "salario_desvio_padrao": df_trab["salario_valido"].std(),
                    "remuneracao_relativa_mediana": df_trab["salario_relativo_referencia"].median(),
                    "n_admitidos_com_referencia": df_trab["salario_relativo_referencia"].count(),
                }
            ]
        )

    out["movimentacoes"] = out["admissoes"] + out["desligamentos"]
    out["saldo"] = out["admissoes"] - out["desligamentos"]

    # Denominadores estaduais para cálculo de participação em SC
    if "competencia" in chaves:
        totais_mes = (
            df_trab.groupby("competencia", dropna=False, observed=True)
            .agg(
                denominador_admissoes_sc=("admissoes", "sum"),
                denominador_desligamentos_sc=("desligamentos", "sum"),
                denominador_movimentacoes_sc=("saldo_mov", "size"),
            )
            .reset_index()
        )
        out = out.merge(totais_mes, on="competencia", how="left", validate="many_to_one")
    else:
        out["denominador_admissoes_sc"] = df_trab["admissoes"].sum()
        out["denominador_desligamentos_sc"] = df_trab["desligamentos"].sum()
        out["denominador_movimentacoes_sc"] = len(df_trab)

    for medida in ["admissoes", "desligamentos", "movimentacoes"]:
        denominador_sc = out[f"denominador_{medida}_sc"].replace(0, float("nan"))
        out[f"pct_{medida}_total_sc"] = 100.0 * out[medida] / denominador_sc

    desligamentos_nao_zero = out["desligamentos"].replace(0, float("nan"))
    out["pct_desligamentos_a_pedido_desligamentos_grupo"] = (
        100.0 * out["desligamentos_a_pedido"] / desligamentos_nao_zero
    )
    out["pct_demissoes_empresa_desligamentos_grupo"] = (
        100.0 * out["demissoes_sem_justa_causa"] / desligamentos_nao_zero
    )
    out["pct_terminos_contrato_desligamentos_grupo"] = (
        100.0 * out["terminos_contrato"] / desligamentos_nao_zero
    )

    # Proporção de pedidos de demissão (40) sobre saídas não-temporárias (40 + 31)
    saidas_nao_temporarias = (
        out["desligamentos_a_pedido"] + out["demissoes_sem_justa_causa"]
    ).replace(0, float("nan"))
    out["pct_pedido_sobre_saidas_nao_temporarias"] = (
        100.0 * out["desligamentos_a_pedido"] / saidas_nao_temporarias
    )

    movimentacoes_nao_zero = out["movimentacoes"].replace(0, float("nan"))
    out["pct_salarios_validos_movimentacoes_grupo"] = (
        100.0 * out["salarios_validos"] / movimentacoes_nao_zero
    )
    out["remuneracao_relativa_pct_referencia"] = (
        out["remuneracao_relativa_mediana"] * 100.0
    )

    return out


def distribuicao(
    df: pd.DataFrame,
    dimensoes: list[str],
    categoria: str,
    coluna_movimento: str = "tipo_mov",
) -> pd.DataFrame:
    """
    Calcula a quantidade e a distribuição percentual de uma variável categórica
    (ex: escolaridade ou faixa_salarial) dentro de cada grupo e tipo de movimentação.
    """
    chaves_agrupamento = dimensoes + [coluna_movimento, categoria]
    resultado = (
        df.groupby(chaves_agrupamento, dropna=False, observed=True)
        .size()
        .rename("quantidade")
        .reset_index()
    )

    chaves_denominador = dimensoes + [coluna_movimento]
    denominador = resultado.groupby(
        chaves_denominador, dropna=False, observed=True
    )["quantidade"].transform("sum")

    resultado["denominador_total_grupo_tipo_mov"] = denominador
    denominador_valido = denominador.where(denominador != 0)
    resultado["percentual_grupo_tipo_mov"] = (
        resultado["quantidade"] / denominador_valido
    ) * 100.0

    return resultado


def exportar(tabelas: dict[str, pd.DataFrame], pasta_destino: Path) -> None:
    """Exporta um dicionário de DataFrames como arquivos CSV em UTF-8 com BOM e separador ';'."""
    pasta_destino.mkdir(parents=True, exist_ok=True)
    for nome_arquivo, tabela in tabelas.items():
        caminho_csv = pasta_destino / f"{nome_arquivo}.csv"
        tabela.to_csv(caminho_csv, sep=";", encoding="utf-8-sig", index=False)


def dados_comuns(args) -> tuple[pd.DataFrame, dict]:
    """Ponto de entrada auxiliar que carrega a base e salva o arquivo de auditoria JSON."""
    args.saida.mkdir(parents=True, exist_ok=True)
    df, auditoria = carregar(args)
    caminho_auditoria = args.saida / "auditoria.json"
    caminho_auditoria.write_text(
        json.dumps(auditoria, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return df, auditoria
