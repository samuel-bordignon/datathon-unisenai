"""Indicadores e hipóteses do painel, calculados sobre os registros selecionados."""
import numpy as np
import pandas as pd

# Item 01: a macrofamília não entra na chave; cada município × setor aparece uma vez.
DIMENSOES = ['codigo_ibge_7d', 'nome_municipio', 'codigo_regiao_imediata',
             'regiao_imediata', 'cnae_divisao', 'setor']


def macrofamilia_predominante(df, dimensoes):
    """Macrofamília com mais movimentações em cada grupo e sua participação no grupo."""
    contagem = df.groupby(dimensoes + ['macrofamilia'], dropna=False, observed=True).size().rename('n').reset_index()
    contagem['total'] = contagem.groupby(dimensoes, dropna=False, observed=True).n.transform('sum')
    topo = contagem.sort_values(['n', 'macrofamilia'], ascending=[False, True]).drop_duplicates(dimensoes)
    topo['pct_macrofamilia_predominante'] = 100 * topo.n / topo.total
    return topo.rename(columns={'macrofamilia': 'macrofamilia_predominante'})[
        dimensoes + ['macrofamilia_predominante', 'pct_macrofamilia_predominante']]


def dividir(numerador, denominador):
    """Divisão com denominador nulo representado como indisponível."""
    if np.isscalar(denominador):
        return numerador / denominador if pd.notna(denominador) and denominador != 0 else numerador * np.nan
    return numerador.div(denominador.where(denominador.ne(0)))


def agregar(df, dimensoes):
    """Agrega fluxos e calcula salários a partir dos registros, não de medianas."""
    base = df.assign(_grupo=1) if not dimensoes else df
    chaves = dimensoes or ['_grupo']
    out = base.groupby(chaves, dropna=False, observed=True).agg(
        admissoes=('admissoes', 'sum'), desligamentos=('desligamentos', 'sum'),
        pedidos=('desligamentos_a_pedido', 'sum'), salarios_validos=('salario_valido', 'count'),
        salario_medio=('salario_valido', 'mean'), salario_mediano=('salario_valido', 'median'),
        n_referencia=('salario_relativo_referencia', 'count'),
        remuneracao_relativa=('salario_relativo_referencia', 'median')).reset_index()
    if not dimensoes:
        out = out.drop(columns='_grupo')
    out['movimentacoes'] = out.admissoes + out.desligamentos
    out['saldo'] = out.admissoes - out.desligamentos
    out['pct_pedidos'] = 100 * dividir(out.pedidos, out.desligamentos)
    out['cobertura_salarial'] = 100 * dividir(out.salarios_validos, out.movimentacoes)
    out['remuneracao_relativa_pct'] = 100 * out.remuneracao_relativa
    return out


def sinais(estado, recorte):
    """Critérios estaduais no período, aplicados aos grupos do recorte."""
    referencia = agregar(estado, DIMENSOES)
    elegiveis = referencia.loc[referencia.movimentacoes.ge(30), 'movimentacoes']
    limiar = elegiveis.quantile(.75) if not elegiveis.empty else np.nan
    pedidos_sc = dividir(estado.desligamentos_a_pedido.sum() * 100, estado.desligamentos.sum())
    grupos = agregar(recorte, DIMENSOES)
    grupos['limiar_movimentacoes'] = limiar
    grupos['pct_pedidos_sc'] = pedidos_sc
    grupos['sinal_retencao'] = (grupos.movimentacoes.ge(30) & grupos.movimentacoes.ge(limiar)
        & grupos.pct_pedidos.gt(pedidos_sc) & grupos.n_referencia.ge(30)
        & grupos.remuneracao_relativa.lt(1))
    if 'macrofamilia' in recorte.columns and not grupos.empty:
        grupos = grupos.merge(macrofamilia_predominante(recorte, DIMENSOES), on=DIMENSOES, how='left', validate='one_to_one')
    return grupos


def municipios(estado, recorte):
    """Quartil de saldo por população definido sobre municípios de SC no período."""
    dims = ['codigo_ibge_7d', 'nome_municipio', 'populacao_estimada_2026']
    def calcular(df):
        out = agregar(df, dims)
        out['saldo_10000'] = 10000 * dividir(out.saldo, out.populacao_estimada_2026.where(out.populacao_estimada_2026.gt(0)))
        return out
    referencia = calcular(estado)
    limiar = referencia.saldo_10000.quantile(.75)
    out = calcular(recorte)
    out['expansao_expressiva'] = out.saldo.gt(0) & out.saldo_10000.ge(limiar)
    out['limiar_10000_sc'] = limiar
    saldo_sc = estado.admissoes.sum() - estado.desligamentos.sum()
    out['saldo_sc'] = saldo_sc
    out['pct_saldo_sc'] = 100 * dividir(out.saldo, saldo_sc)
    return out


def distribuicao(df, categoria):
    out = df.groupby(['tipo_mov', categoria], dropna=False, observed=True).size().rename('quantidade').reset_index()
    total = out.groupby('tipo_mov', observed=True).quantidade.transform('sum')
    out['denominador'] = total
    out['percentual'] = 100 * dividir(out.quantidade, total)
    return out


def evolucao(df):
    out = agregar(df, ['competencia']).sort_values('competencia')
    for coluna in ['admissoes', 'saldo']:
        anterior = out[coluna].shift()
        out[f'variacao_{coluna}'] = out[coluna] - anterior
        out[f'variacao_{coluna}_pct'] = 100 * dividir(out[f'variacao_{coluna}'], anterior.where(anterior.gt(0)))
    return out
