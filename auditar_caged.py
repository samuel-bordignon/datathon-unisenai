"""Auditoria integral do CSV legível contra a origem e o dicionário.

Não modifica o CSV. Lê os dois arquivos em blocos, refaz as traduções e compara
cada uma das 3.397.416 linhas e 28 colunas.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
import math
import time

import pandas as pd

GERADOS = Path(__file__).resolve().parent
BASE = GERADOS.parent
ORIGINAL = BASE / "Novo_Caged_MOV_Limpo.csv"
DICIONARIO = BASE / "Dicionario_de_dados.xlsx"
LEGIVEL = GERADOS / "Novo_Caged_MOV_Legivel.csv"
RELATORIO = GERADOS / "relatorio_auditoria_integral.txt"
CHUNK = 100_000

NOMES = {
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
NUMERICAS = {
    "saldomovimentação": "int",
    "idade": "int",
    "horascontratuais": "float",
    "salário": "float",
    "valorsaláriofixo": "float",
}
COMPETENCIAS = {"competênciamov", "competênciadec"}


def norm(v):
    """Replica exatamente a normalização do script gerador."""
    if pd.isna(v):
        return None
    s = str(v).strip()
    try:
        return str(int(float(s.replace(",", "."))))
    except ValueError:
        return s.upper()


def iguais_texto(a: pd.Series, b: pd.Series) -> pd.Series:
    return a.fillna("<NULO>").astype(str).eq(b.fillna("<NULO>").astype(str))


def iguais_numero(orig: pd.Series, saida: pd.Series, tipo: str) -> pd.Series:
    esperado = pd.to_numeric(orig.str.replace(",", ".", regex=False), errors="coerce")
    obtido = pd.to_numeric(saida.str.replace(",", ".", regex=False), errors="coerce")
    if tipo == "int":
        # O gerador converte estes campos a Int64.
        esperado = esperado.astype("Int64")
        obtido = obtido.astype("Int64")
    return esperado.eq(obtido) | (esperado.isna() & obtido.isna())


inicio = time.time()
problemas: list[str] = []
avisos: list[str] = []

# Cabeçalhos e anomalia estrutural conhecida da origem.
with ORIGINAL.open("r", encoding="utf-8", newline="") as f:
    cab_original_bruto = f.readline().rstrip("\r\n").split(";")
    primeira_linha_campos = len(f.readline().rstrip("\r\n").split(";"))
colunas_origem = ["_idx1", "_idx2"] + cab_original_bruto[1:]
colunas_dados = colunas_origem[2:]

with LEGIVEL.open("r", encoding="utf-8-sig", newline="") as f:
    cab_saida = f.readline().rstrip("\r\n").split(";")
cab_esperado = [NOMES[c] for c in colunas_dados]
if cab_saida != cab_esperado:
    problemas.append(f"Cabeçalho de saída diferente do esperado: {cab_saida!r}")

# Validação estrutural e de conteúdo do dicionário.
xl = pd.ExcelFile(DICIONARIO)
layout = pd.read_excel(xl, "Layout", header=1, dtype=str)
variaveis_layout = set(layout.iloc[:, 0].dropna().str.strip())
abas = [s for s in xl.sheet_names if s != "Layout"]
mapas: dict[str, dict[str, str]] = {}
dict_duplicados: dict[str, list[str]] = {}
dict_descricoes_vazias: dict[str, int] = {}
dict_codigos_fracionarios: dict[str, list[str]] = {}

for aba in abas:
    d = pd.read_excel(xl, aba, dtype=str)
    if d.shape[1] < 2:
        problemas.append(f"Aba {aba!r} tem menos de duas colunas")
        continue
    cod = d.iloc[:, 0]
    desc = d.iloc[:, 1]
    normalizados = cod.map(norm)
    duplicados = sorted(normalizados[normalizados.duplicated(keep=False) & normalizados.notna()].unique())
    if duplicados:
        dict_duplicados[aba] = duplicados
    vazias = int(desc.isna().sum() + desc.fillna("").str.strip().eq("").sum())
    if vazias:
        dict_descricoes_vazias[aba] = vazias
    fracionarios = []
    for valor in cod.dropna().astype(str):
        s = valor.strip().replace(",", ".")
        try:
            n = float(s)
            if math.isfinite(n) and not n.is_integer():
                fracionarios.append(valor)
        except ValueError:
            pass
    if fracionarios:
        dict_codigos_fracionarios[aba] = sorted(set(fracionarios))
    mapas[aba] = {
        norm(c): str(descricao).strip()
        for c, descricao in zip(cod, desc)
        if norm(c) is not None and pd.notna(descricao) and str(descricao).strip()
    }

if dict_duplicados:
    problemas.append(f"Há códigos duplicados após normalização no dicionário: {dict_duplicados}")
if dict_descricoes_vazias:
    problemas.append(f"Há descrições vazias no dicionário: {dict_descricoes_vazias}")
if dict_codigos_fracionarios:
    problemas.append(f"Há códigos fracionários no dicionário: {dict_codigos_fracionarios}")

colunas_mapeaveis = [c for c in colunas_dados if c in mapas]
colunas_sem_aba = [c for c in colunas_dados if c not in mapas and c not in NUMERICAS and c not in COMPETENCIAS]
abas_nao_usadas = sorted(set(abas) - set(colunas_dados))
layout_ausente_origem = sorted(variaveis_layout - set(colunas_dados))
origem_ausente_layout = sorted(set(colunas_dados) - variaveis_layout)
if colunas_sem_aba:
    problemas.append(f"Colunas categóricas sem aba no dicionário: {colunas_sem_aba}")
if origem_ausente_layout:
    problemas.append(f"Colunas da origem ausentes do Layout: {origem_ausente_layout}")
if layout_ausente_origem:
    avisos.append(f"Variáveis do Layout que não existem no CSV original: {layout_ausente_origem}")
if abas_nao_usadas:
    avisos.append(f"Abas do dicionário não usadas porque a variável não existe no CSV original: {abas_nao_usadas}")

# Leitura e comparação integral em blocos.
orig_it = pd.read_csv(
    ORIGINAL, sep=";", skiprows=1, header=None, names=colunas_origem,
    dtype=str, encoding="utf-8", chunksize=CHUNK,
)
saida_it = pd.read_csv(
    LEGIVEL, sep=";", dtype=str, encoding="utf-8-sig", chunksize=CHUNK,
)

linhas_origem = 0
linhas_saida = 0
mismatches = Counter()
primeiros_erros: dict[str, list[str]] = defaultdict(list)
nao_mapeados_contagem = Counter()
nao_mapeados_codigos: dict[str, set[str]] = defaultdict(set)
nulos_origem = Counter()
nulos_saida = Counter()
idx1_erros = 0
idx2_nulos = 0
idx2_nao_crescente = 0
idx2_anterior: int | None = None
competencias_invalidas = Counter()

for numero_bloco, par in enumerate(zip_longest(orig_it, saida_it), start=1):
    orig, out = par
    if orig is None:
        linhas_saida += len(out)
        problemas.append("A saída contém blocos adicionais além do fim da origem")
        continue
    if out is None:
        linhas_origem += len(orig)
        problemas.append("A saída terminou antes da origem")
        continue

    base_linha = linhas_origem + 2  # primeira linha de dados está na linha física 2
    linhas_origem += len(orig)
    linhas_saida += len(out)
    if len(orig) != len(out):
        problemas.append(f"Bloco {numero_bloco}: origem={len(orig)}, saída={len(out)}")

    # Os dois campos sem cabeçalho são índices/proveniência, não dados do Layout.
    idx1 = pd.to_numeric(orig["_idx1"], errors="coerce")
    esperado_idx1 = pd.Series(range(linhas_origem - len(orig), linhas_origem), index=orig.index)
    idx1_erros += int((idx1 != esperado_idx1).sum())
    idx2 = pd.to_numeric(orig["_idx2"], errors="coerce")
    idx2_nulos += int(idx2.isna().sum())
    for valor in idx2.dropna().astype("int64"):
        if idx2_anterior is not None and valor <= idx2_anterior:
            idx2_nao_crescente += 1
        idx2_anterior = int(valor)

    for c in colunas_dados:
        nulos_origem[c] += int(orig[c].isna().sum())
        nome_saida = NOMES[c]
        if nome_saida not in out.columns:
            mismatches[c] += len(orig)
            continue
        nulos_saida[nome_saida] += int(out[nome_saida].isna().sum())

        if c in mapas:
            codigos = orig[c].map(norm)
            esperado = codigos.map(mapas[c])
            sem_mapa = esperado.isna() & codigos.notna()
            if sem_mapa.any():
                nao_mapeados_contagem[c] += int(sem_mapa.sum())
                nao_mapeados_codigos[c].update(codigos[sem_mapa].unique())
                esperado.loc[sem_mapa] = "Código " + codigos[sem_mapa] + " (não consta no dicionário)"
            if c == "município":
                esperado = esperado.str.replace(r"^[A-Za-z]{2}-", "", regex=True)
            ok = iguais_texto(esperado.reset_index(drop=True), out[nome_saida].reset_index(drop=True))
        elif c in COMPETENCIAS:
            esperado = orig[c].str[:4] + "-" + orig[c].str[4:6]
            valido = orig[c].fillna("").str.fullmatch(r"\d{6}") & orig[c].str[4:6].isin([f"{m:02d}" for m in range(1, 13)])
            competencias_invalidas[c] += int((~valido).sum())
            ok = iguais_texto(esperado.reset_index(drop=True), out[nome_saida].reset_index(drop=True))
        elif c in NUMERICAS:
            ok = iguais_numero(orig[c].reset_index(drop=True), out[nome_saida].reset_index(drop=True), NUMERICAS[c])
        else:
            ok = iguais_texto(orig[c].reset_index(drop=True), out[nome_saida].reset_index(drop=True))

        qtd = int((~ok).sum())
        mismatches[c] += qtd
        if qtd and len(primeiros_erros[c]) < 5:
            posicoes = list(ok[~ok].index[: 5 - len(primeiros_erros[c])])
            for pos in posicoes:
                primeiros_erros[c].append(
                    f"linha {base_linha + pos}: origem={orig[c].iloc[pos]!r}; saída={out[nome_saida].iloc[pos]!r}"
                )

if idx1_erros:
    problemas.append(f"Primeiro índice não sequencial em {idx1_erros} linhas")
if idx2_nulos:
    problemas.append(f"Segundo índice tem {idx2_nulos} valores nulos/não numéricos")
if idx2_nao_crescente:
    avisos.append(f"Segundo índice não é estritamente crescente em {idx2_nao_crescente} transições")
if any(competencias_invalidas.values()):
    problemas.append(f"Competências inválidas na origem: {dict(competencias_invalidas)}")
if linhas_origem != linhas_saida:
    problemas.append(f"Contagens divergentes: origem={linhas_origem}, saída={linhas_saida}")
if any(mismatches.values()):
    problemas.append(f"Valores divergentes por coluna: {dict(mismatches)}")

# Relatório durável.
tempo = time.time() - inicio
with RELATORIO.open("w", encoding="utf-8") as r:
    r.write("AUDITORIA INTEGRAL DO NOVO CAGED\n")
    r.write("=" * 36 + "\n\n")
    r.write(f"Arquivo original: {ORIGINAL}\n")
    r.write(f"Arquivo validado: {LEGIVEL}\n")
    r.write(f"Dicionário: {DICIONARIO}\n")
    r.write(f"Linhas de dados na origem: {linhas_origem}\n")
    r.write(f"Linhas de dados na saída: {linhas_saida}\n")
    r.write(f"Colunas de dados: {len(colunas_dados)}\n")
    r.write(f"Células de dados comparadas: {linhas_origem * len(colunas_dados):,}\n")
    r.write(f"Tempo de auditoria: {tempo:.1f} segundos\n\n")

    r.write("RESULTADO\n--------\n")
    if problemas:
        r.write("REPROVADO: foram encontrados problemas que afetam a confirmação integral.\n")
    else:
        r.write("APROVADO: todas as células geradas correspondem à transformação definida.\n")
    r.write(f"Divergências entre origem+dicionário e CSV gerado: {sum(mismatches.values())}\n")
    r.write(f"Cabeçalho final correto: {'SIM' if cab_saida == cab_esperado else 'NÃO'}\n")
    r.write(f"Linhas preservadas: {'SIM' if linhas_origem == linhas_saida else 'NÃO'}\n")
    r.write(f"Primeiro índice original sequencial: {'SIM' if idx1_erros == 0 else 'NÃO'}\n")
    r.write(f"Segundo índice original preenchido: {'SIM' if idx2_nulos == 0 else 'NÃO'}\n\n")

    r.write("ESTRUTURA DA ORIGEM\n-------------------\n")
    r.write(f"Campos no cabeçalho bruto: {len(cab_original_bruto)}\n")
    r.write(f"Campos na primeira linha de dados: {primeira_linha_campos}\n")
    r.write("O cabeçalho funde os nomes de dois índices em um campo; o script recompõe 30 posições e remove os dois índices.\n")
    r.write("Esses índices não constam no Layout do CAGED; o segundo preserva a posição/proveniência da base anterior.\n\n")

    r.write("DICIONÁRIO\n----------\n")
    r.write(f"Colunas traduzidas por abas: {len(colunas_mapeaveis)} -> {colunas_mapeaveis}\n")
    r.write(f"Duplicidades após normalização: {dict_duplicados or 'nenhuma'}\n")
    r.write(f"Descrições vazias: {dict_descricoes_vazias or 'nenhuma'}\n")
    r.write(f"Códigos fracionários: {dict_codigos_fracionarios or 'nenhum'}\n")
    r.write(f"Abas não usadas: {abas_nao_usadas or 'nenhuma'}\n")
    r.write(f"Variáveis do Layout ausentes do CSV original: {layout_ausente_origem or 'nenhuma'}\n\n")

    r.write("CÓDIGOS SEM DESCRIÇÃO NO DICIONÁRIO\n-----------------------------------\n")
    if nao_mapeados_contagem:
        for c in sorted(nao_mapeados_contagem):
            r.write(f"{c}: {nao_mapeados_contagem[c]} linhas; códigos={sorted(nao_mapeados_codigos[c])}\n")
        r.write("O CSV preserva esses códigos com a marca '(não consta no dicionário)'.\n")
    else:
        r.write("Nenhum.\n")
    r.write("\n")

    r.write("NULOS\n-----\n")
    r.write("Origem:\n")
    for c in colunas_dados:
        if nulos_origem[c]:
            r.write(f"  {c}: {nulos_origem[c]}\n")
    r.write("Saída:\n")
    for c in cab_esperado:
        if nulos_saida[c]:
            r.write(f"  {c}: {nulos_saida[c]}\n")
    r.write("\n")

    r.write("DIVERGÊNCIAS POR COLUNA\n-----------------------\n")
    for c in colunas_dados:
        r.write(f"{c}: {mismatches[c]}\n")
        for exemplo in primeiros_erros.get(c, []):
            r.write(f"  {exemplo}\n")
    r.write("\n")

    r.write("PROBLEMAS\n---------\n")
    if problemas:
        for p in problemas:
            r.write(f"- {p}\n")
    else:
        r.write("Nenhum problema de correspondência ou integridade encontrado.\n")
    r.write("\nAVISOS E LIMITAÇÕES\n-------------------\n")
    for a in avisos:
        r.write(f"- {a}\n")
    r.write("- O CSV legível substitui códigos categóricos por descrições; os códigos oficiais não são mantidos em colunas paralelas.\n")
    r.write("- Idade, horas e valores monetários passam por conversão numérica; zeros decimais de apresentação podem ser removidos.\n")
    r.write("- Esta auditoria confirma fidelidade ao arquivo original e ao dicionário fornecido, não a exatidão externa do conteúdo publicado pelo CAGED.\n")

print(str(RELATORIO))
print("APROVADO" if not problemas else "REPROVADO")
