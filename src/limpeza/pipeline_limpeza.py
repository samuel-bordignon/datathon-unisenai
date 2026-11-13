from pathlib import Path
import pandas as pd

from limpeza_municipios import carregar_e_limpar_municipios
from limpeza_caged import carregar_e_limpar_caged
from cruzamento_dados import realizar_inner_join_caged_municipios
from exportacao_dados import exportar_base_limpa_csv


def executar_pipeline_limpeza() -> pd.DataFrame:
    """
    Responsabilidade:
    Orquestrar a chamada dos módulos de limpeza, cruzamento relacional
    e exportação da base limpa final em CSV.
    """
    # O diretório raiz do projeto fica dois níveis acima de src/limpeza/
    diretorio_base = Path(__file__).resolve().parent.parent.parent
    caminho_municipios = diretorio_base / "database" / "doc" / "Municipios_SC_limpo.csv"
    caminho_caged = diretorio_base / "database" / "doc" / "Novo_Caged_MOV_Limpo.csv"
    caminho_saida = (
        diretorio_base / "database" / "doc" / "Caged_Industrial_SC_Limpo_Unificado.csv"
    )

    print("==================================================")
    print("ETAPA 1: LIMPEZA DOS MUNICÍPIOS")
    print("==================================================")
    df_municipios_limpo = carregar_e_limpar_municipios(caminho_municipios)

    print("\n==================================================")
    print("ETAPA 2: LIMPEZA E FILTRAGEM DO CAGED (SEÇÕES B a F)")
    print("==================================================")
    df_caged_limpo = carregar_e_limpar_caged(caminho_caged)

    print("\n==================================================")
    print("ETAPA 3: CRUZAMENTO RELACIONAL (INNER JOIN)")
    print("==================================================")
    df_final = realizar_inner_join_caged_municipios(
        df_caged=df_caged_limpo,
        df_municipios=df_municipios_limpo,
    )

    print("\n==================================================")
    print("ETAPA 4: EXPORTAÇÃO DA BASE LIMPA EM CSV")
    print("==================================================")
    exportar_base_limpa_csv(
        df_unificado=df_final,
        caminho_saida_csv=caminho_saida,
    )

    print("\n==================================================")
    print("RESUMO DA BASE FINAL UNIFICADA")
    print("==================================================")
    print(f"Total de linhas salvas: {len(df_final)}")
    print(f"Arquivo gerado em: {caminho_saida}")

    return df_final


if __name__ == "__main__":
    base_unificada = executar_pipeline_limpeza()
