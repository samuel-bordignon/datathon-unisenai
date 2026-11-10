"""Decodifica o Novo CAGED (movimentações) usando o Dicionario_de_dados.xlsx.

Gera Novo_Caged_MOV_Legivel.csv com os códigos substituídos pelas descrições.

Como usar:
    1. Coloque Novo_Caged_MOV_Limpo.csv e Dicionario_de_dados.xlsx na mesma
       pasta deste script.
    2. Rode: python decodificar_caged.py

O resultado (Novo_Caged_MOV_Legivel.csv e relatorio_decodificacao.txt) é
gravado na mesma pasta do script. Nenhuma subpasta é criada ou necessária.

Se os dados não estiverem na pasta do script, ele também procura uma e duas
pastas acima. Para usar outra pasta, informe o caminho:
    python decodificar_caged.py "C:\\caminho\\dos\\dados"
"""
import sys
from pathlib import Path

import pandas as pd

NOME_ENTRADA = "Novo_Caged_MOV_Limpo.csv"
NOME_DICIONARIO = "Dicionario_de_dados.xlsx"

PASTA_SCRIPT = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    CANDIDATAS = [Path(sys.argv[1]).expanduser().resolve()]
else:
    CANDIDATAS = [PASTA_SCRIPT, PASTA_SCRIPT.parent, PASTA_SCRIPT.parent.parent]
PASTA_DADOS = next(
    (p for p in CANDIDATAS
     if (p / NOME_ENTRADA).is_file() and (p / NOME_DICIONARIO).is_file()),
    None,
)
if PASTA_DADOS is None:
    raise SystemExit(
        f"Não encontrei {NOME_ENTRADA} e {NOME_DICIONARIO} juntos em:\n"
        + "\n".join(f"  {p}" for p in CANDIDATAS)
        + "\nColoque os dois arquivos na mesma pasta deste script ou informe a pasta:\n"
        + '  python decodificar_caged.py "C:\\caminho\\dos\\dados"'
    )

ENTRADA = PASTA_DADOS / NOME_ENTRADA
DICIONARIO = PASTA_DADOS / NOME_DICIONARIO
SAIDA = PASTA_SCRIPT / "Novo_Caged_MOV_Legivel.csv"
RELATORIO = PASTA_SCRIPT / "relatorio_decodificacao.txt"
print(f"Lendo dados de: {PASTA_DADOS}")
print(f"Gravando em:    {PASTA_SCRIPT}")


def norm(v):
    """Normaliza códigos: '97', 97, 97.0 -> '97'; letras ficam em maiúsculo."""
    if pd.isna(v):
        return None
    s = str(v).strip()
    try:
        return str(int(float(s.replace(",", "."))))
    except ValueError:
        return s.upper()


# --- Leitura do CSV (cabeçalho tem as 2 colunas de índice fundidas em uma) ---
with open(ENTRADA, encoding="utf-8") as f:
    header = f.readline().rstrip("\r\n").split(";")
colunas = ["_idx1", "_idx2"] + header[1:]
df = pd.read_csv(ENTRADA, sep=";", skiprows=1, header=None, names=colunas,
                 dtype=str, encoding="utf-8")
df = df.drop(columns=["_idx1", "_idx2"])
n_original = len(df)

# --- Decodificação com cada aba do dicionário ---
xl = pd.ExcelFile(DICIONARIO)
abas = [s for s in xl.sheet_names if s != "Layout"]
nao_mapeados = {}
for col in df.columns:
    if col not in abas:
        continue
    d = pd.read_excel(xl, col, dtype=str)
    mapa = {norm(c): str(desc).strip() for c, desc in zip(d.iloc[:, 0], d.iloc[:, 1])}
    codigos = df[col].map(norm)
    decod = codigos.map(mapa)
    sem_par = decod.isna() & codigos.notna()
    if sem_par.any():
        nao_mapeados[col] = (int(sem_par.sum()), sorted(codigos[sem_par].unique()))
    # Código ausente no dicionário: deixa explícito em vez de apagar
    decod[sem_par] = "Código " + codigos[sem_par] + " (não consta no dicionário)"
    df[col] = decod

# --- Ajustes de formato ---
# Dicionário traz municípios como "Sc-Florianopolis"; remove o prefixo da UF
df["município"] = df["município"].str.replace(r"^[A-Za-z]{2}-", "", regex=True)
for c in ["competênciamov", "competênciadec"]:
    df[c] = df[c].str[:4] + "-" + df[c].str[4:6]
for c in ["salário", "valorsaláriofixo", "horascontratuais"]:
    df[c] = pd.to_numeric(df[c].str.replace(",", ".", regex=False), errors="coerce")
df["idade"] = pd.to_numeric(df["idade"], errors="coerce").astype("Int64")
df["saldomovimentação"] = pd.to_numeric(df["saldomovimentação"], errors="coerce").astype("Int64")

# --- Nomes de colunas legíveis ---
nomes = {
    "competênciamov": "competencia_movimentacao",
    "região": "regiao",
    "uf": "uf",
    "município": "municipio",
    "seção": "secao_cnae",
    "subclasse": "subclasse_cnae",
    "saldomovimentação": "saldo_movimentacao",
    "cbo2002ocupação": "ocupacao_cbo2002",
    "categoria": "categoria_trabalhador",
    "graudeinstrução": "grau_instrucao",
    "idade": "idade",
    "horascontratuais": "horas_contratuais_semanais",
    "raçacor": "raca_cor",
    "sexo": "sexo",
    "tipoempregador": "tipo_empregador",
    "tipoestabelecimento": "tipo_estabelecimento",
    "tipomovimentação": "tipo_movimentacao",
    "tipodedeficiência": "tipo_deficiencia",
    "indtrabintermitente": "trabalho_intermitente",
    "indtrabparcial": "trabalho_parcial",
    "salário": "salario_mensal",
    "tamestabjan": "tamanho_estabelecimento_jan",
    "indicadoraprendiz": "aprendiz",
    "origemdainformação": "origem_informacao",
    "competênciadec": "competencia_declaracao",
    "indicadordeforadoprazo": "declarado_fora_do_prazo",
    "unidadesaláriocódigo": "unidade_salario",
    "valorsaláriofixo": "valor_salario_fixo",
}
df = df.rename(columns=nomes)

# Separador ';' e vírgula decimal para abrir direto no Excel em português
df.to_csv(SAIDA, sep=";", decimal=",", index=False, encoding="utf-8-sig")

with open(RELATORIO, "w", encoding="utf-8") as r:
    r.write(f"Linhas lidas: {n_original} | gravadas: {len(df)}\n")
    r.write("Códigos sem correspondência no dicionário (coluna: linhas afetadas, códigos):\n")
    for col, (n, cods) in nao_mapeados.items():
        r.write(f"  {col}: {n} linhas -> {cods}\n")
    r.write("\nNulos por coluna:\n" + df.isna().sum().to_string() + "\n")
    r.write("\nAmostra:\n" + df.head(3).T.to_string() + "\n")
