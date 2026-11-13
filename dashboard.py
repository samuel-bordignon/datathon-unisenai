"""Painel de inteligência territorial para as movimentações industriais em SC."""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / 'src' / 'analises'))
from cenarios import agregar, distribuicao, evolucao, municipios, sinais
from mapa import orientar_malha

BASE = RAIZ / 'database' / 'resultados' / 'dashboard'
GEO = BASE / 'malha_sc.geojson'
st.set_page_config(page_title='Indústria SC | Inteligência territorial', page_icon='📊', layout='wide')


@st.cache_data(show_spinner='Carregando dados preparados...')
def carregar(caminho, modificacao):
    return pd.read_parquet(caminho)


@st.cache_data
def carregar_geo(caminho, modificacao):
    return orientar_malha(json.loads(Path(caminho).read_text(encoding='utf-8')))


def numero(valor, casas=0):
    if pd.isna(valor):
        return 'Não disponível'
    return f'{valor:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def mostrar_tabela(tabela, colunas, limite=20):
    st.dataframe(tabela[[c for c in colunas if c in tabela.columns]].head(limite),
                 hide_index=True, use_container_width=True)


def barras(df, x, y, titulo, cor=None):
    if df.empty:
        st.info('Não há dados para este recorte.')
        return
    fig = px.bar(df.head(15).iloc[::-1], x=x, y=y, orientation='h', color=cor,
                 title=titulo, template='plotly_white')
    fig.update_layout(height=470, margin=dict(l=10, r=10, t=50, b=10), yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


def perfil(df):
    if df.empty:
        st.info('Não há movimentações neste recorte.')
        return
    esquerda, direita = st.columns(2)
    with esquerda:
        educ = distribuicao(df, 'escolaridade')
        st.plotly_chart(px.bar(educ, x='percentual', y='escolaridade', color='tipo_mov',
            barmode='group', orientation='h', hover_data=['quantidade', 'denominador'],
            labels={'percentual': '% do tipo de movimentação', 'escolaridade': 'Escolaridade'},
            title='Escolaridade observada', template='plotly_white'), use_container_width=True)
    with direita:
        sal = agregar(df, ['tipo_mov'])
        st.subheader('Remuneração mensal nominal')
        mostrar_tabela(sal, ['tipo_mov', 'movimentacoes', 'salarios_validos', 'cobertura_salarial',
                             'salario_medio', 'salario_mediano', 'n_referencia', 'remuneracao_relativa_pct'])
        st.caption('Referência relativa: mediana das razões individuais dos admitidos, comparadas à mediana estadual da mesma escolaridade e competência. Interpretação requer ao menos 30 salários com referência.')


if not (BASE / 'movimentacoes.parquet').exists():
    st.title('Indústria SC | Inteligência territorial')
    st.warning('A base do painel ainda não foi preparada. Execute: `python src/analises/preparar_dashboard.py`')
    st.stop()

df = carregar(str(BASE / 'movimentacoes.parquet'), (BASE / 'movimentacoes.parquet').stat().st_mtime_ns)
meta = json.loads((BASE / 'metadados.json').read_text(encoding='utf-8'))
st.title('Indústria SC | Inteligência territorial')
st.caption('Novo CAGED · fluxos de emprego industrial · hipóteses para orientar investigação')
competencias = sorted(df.competencia.unique().tolist())
with st.sidebar:
    st.header('Filtros')
    inicio, fim = st.select_slider('Competências', options=competencias, value=(competencias[0], competencias[-1]),
                                    format_func=lambda x: f'{str(x)[4:]}/{str(x)[:4]}')
    estado = df[df.competencia.between(inicio, fim)]
    regioes = st.multiselect('Região imediata', sorted(estado.regiao_imediata.dropna().unique()))
    territorio = estado[estado.regiao_imediata.isin(regioes)] if regioes else estado
    cidades = st.multiselect('Município', sorted(territorio.nome_municipio.dropna().unique()))
    setores = st.multiselect('Divisão CNAE', sorted(estado.setor.dropna().unique()))
    st.caption('Sem seleção, todos os valores da dimensão são incluídos.')
recorte = territorio
if cidades:
    recorte = recorte[recorte.nome_municipio.isin(cidades)]
if setores:
    recorte = recorte[recorte.setor.isin(setores)]
st.caption(f'Período: {inicio}–{fim} · {numero(len(recorte))} movimentações no recorte · Base gerada em {meta["gerado_em_utc"][:10]}')
if recorte.empty:
    st.warning('Não há movimentações para a combinação de filtros selecionada.')
    st.stop()

pagina = st.radio('Navegação', ['Visão geral', 'Sinais de apagão', 'Expansão acelerada',
    'Análise territorial', 'Qualificação e remuneração', 'Diagnóstico e recomendações'], horizontal=True,
    label_visibility='collapsed')

if pagina == 'Visão geral':
    total = agregar(recorte, []).iloc[0]
    cols = st.columns(5)
    for col, label, valor in zip(cols, ['Admissões', 'Desligamentos', 'Saldo', 'Municípios', 'Setores CNAE'],
        [total.admissoes, total.desligamentos, total.saldo, recorte.codigo_ibge_7d.nunique(), recorte.cnae_divisao.nunique()]):
        col.metric(label, numero(valor))
    mensal = evolucao(recorte)
    fig = px.line(mensal, x='competencia', y=['admissoes', 'desligamentos', 'saldo'], markers=True,
                  title='Movimentações por competência', labels={'value': 'Movimentações', 'competencia': 'Competência'}, template='plotly_white')
    fig.update_xaxes(type='category')
    st.plotly_chart(fig, use_container_width=True)
    barras(municipios(estado, recorte).sort_values('movimentacoes', ascending=False), 'movimentacoes', 'nome_municipio', 'Municípios com mais movimentações')

elif pagina == 'Sinais de apagão':
    st.subheader('Combinações que merecem investigação')
    st.info('Sinal exploratório, não diagnóstico de apagão: volume elevado, pedidos acima da proporção estadual e remuneração relativa inferior à referência, com amostra suficiente.')
    grupos = sinais(estado, recorte)
    alertas = grupos[grupos.sinal_retencao].sort_values('movimentacoes', ascending=False)
    if alertas.empty:
        st.info('Nenhuma combinação atende simultaneamente aos critérios neste recorte.')
    else:
        mostrar_tabela(alertas, ['nome_municipio', 'setor', 'macrofamilia_predominante', 'pct_macrofamilia_predominante', 'movimentacoes', 'admissoes', 'desligamentos', 'saldo', 'pedidos', 'pct_pedidos', 'pct_pedidos_sc', 'n_referencia', 'remuneracao_relativa_pct', 'limiar_movimentacoes'])
        opcoes = {f"{r.nome_municipio} | {r.setor}": (r.codigo_ibge_7d, r.cnae_divisao) for r in alertas.itertuples()}
        escolha = st.selectbox('Investigar combinação', list(opcoes))
        cod, setor = opcoes[escolha]
        detalhe = recorte[(recorte.codigo_ibge_7d == cod) & (recorte.cnae_divisao == setor)]
        perfil(detalhe)
        barras(agregar(detalhe, ['cbo', 'descricao_cbo']).sort_values('movimentacoes', ascending=False), 'movimentacoes', 'descricao_cbo', 'CBOs com mais movimentações')

elif pagina == 'Expansão acelerada':
    mun = municipios(estado, recorte)
    st.caption('O sinal relativo usa saldo positivo e quartil superior do saldo por 10 mil habitantes entre os municípios de SC no período. População municipal estimada de 2026.')
    a, b = st.columns(2)
    with a:
        barras(mun.sort_values('saldo', ascending=False), 'saldo', 'nome_municipio', 'Maiores saldos absolutos')
    with b:
        barras(mun[mun.expansao_expressiva].sort_values('saldo_10000', ascending=False), 'saldo_10000', 'nome_municipio', 'Expansão relativa · saldo por 10 mil habitantes')
    mostrar_tabela(mun.sort_values('saldo', ascending=False), ['nome_municipio', 'admissoes', 'desligamentos', 'saldo', 'populacao_estimada_2026', 'saldo_10000', 'saldo_sc', 'pct_saldo_sc', 'expansao_expressiva'])
    st.caption('A participação no saldo estadual pode superar 100% ou ser negativa quando há saldos de sinais opostos; é indisponível se o saldo estadual for zero.')
    barras(agregar(recorte, ['setor']).sort_values('saldo', ascending=False), 'saldo', 'setor', 'Setores por saldo')
    st.subheader('Evolução mensal e variação em relação ao mês anterior')
    mensal = evolucao(recorte)
    fig = px.line(mensal, x='competencia', y=['admissoes', 'saldo'], markers=True,
                  title='Admissões e saldo por competência', template='plotly_white')
    fig.update_xaxes(type='category')
    st.plotly_chart(fig, use_container_width=True)
    mostrar_tabela(mensal, ['competencia', 'admissoes', 'saldo', 'variacao_admissoes', 'variacao_admissoes_pct', 'variacao_saldo', 'variacao_saldo_pct'])
    st.caption('Variações percentuais são omitidas quando o valor anterior é zero ou negativo.')
    perfil(recorte[recorte.admissoes.eq(1)])
    remuneracao_mensal = agregar(recorte[recorte.admissoes.eq(1)], ['competencia'])
    fig = px.line(remuneracao_mensal, x='competencia', y=['salario_medio', 'salario_mediano'], markers=True,
                  hover_data=['salarios_validos', 'cobertura_salarial'], title='Remuneração nominal dos admitidos por competência', template='plotly_white')
    fig.update_xaxes(type='category')
    st.plotly_chart(fig, use_container_width=True)
    faixas_admitidos = distribuicao(recorte[recorte.admissoes.eq(1)], 'faixa_salarial')
    mostrar_tabela(faixas_admitidos, ['faixa_salarial', 'quantidade', 'denominador', 'percentual'])
    barras(agregar(recorte, ['macrofamilia']).sort_values('admissoes', ascending=False), 'admissoes', 'macrofamilia', 'Macrofamílias com mais admissões')
    barras(agregar(recorte, ['cbo', 'descricao_cbo']).sort_values('admissoes', ascending=False), 'admissoes', 'descricao_cbo', 'CBOs com mais admissões')

elif pagina == 'Análise territorial':
    mun = municipios(estado, recorte)
    escolha = st.selectbox('Indicador no mapa', ['saldo', 'saldo_10000', 'admissoes', 'desligamentos', 'movimentacoes'])
    if GEO.exists():
        geo = carregar_geo(str(GEO), GEO.stat().st_mtime_ns)
        fig = px.choropleth(mun, geojson=geo, locations='codigo_ibge_7d', featureidkey='properties.codarea', color=escolha,
                            hover_name='nome_municipio', hover_data=['admissoes', 'desligamentos', 'saldo', 'saldo_10000'],
                            color_continuous_scale='RdBu', title='Municípios de Santa Catarina')
        fig.update_geos(fitbounds='locations', visible=False)
        fig.update_layout(height=650, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning('Malha municipal não encontrada. Execute obter_referencias.py.')
    mostrar_tabela(mun.sort_values('saldo', ascending=False), ['nome_municipio', 'admissoes', 'desligamentos', 'saldo', 'saldo_10000'])
    fig = px.scatter(mun, x='movimentacoes', y='saldo_10000', hover_name='nome_municipio', size='admissoes',
                     labels={'saldo_10000': 'Saldo por 10 mil habitantes', 'movimentacoes': 'Movimentações'}, title='Volume e saldo relativo', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

elif pagina == 'Qualificação e remuneração':
    familias = st.multiselect('Macrofamília', sorted(recorte.macrofamilia.dropna().unique()))
    detalhe = recorte[recorte.macrofamilia.isin(familias)] if familias else recorte
    perfil(detalhe)
    faixas = distribuicao(detalhe, 'faixa_salarial')
    st.plotly_chart(px.bar(faixas, x='faixa_salarial', y='percentual', color='tipo_mov', barmode='group',
                          hover_data=['quantidade', 'denominador'], title='Faixa salarial em salários mínimos', template='plotly_white'), use_container_width=True)
    familias_tabela = agregar(detalhe, ['macrofamilia']).sort_values('movimentacoes', ascending=False)
    familias_tabela['pct_admissoes_recorte'] = 100 * familias_tabela.admissoes.div(detalhe.admissoes.sum() or float('nan'))
    familias_tabela['pct_desligamentos_recorte'] = 100 * familias_tabela.desligamentos.div(detalhe.desligamentos.sum() or float('nan'))
    mostrar_tabela(familias_tabela,
                   ['macrofamilia', 'admissoes', 'pct_admissoes_recorte', 'desligamentos', 'pct_desligamentos_recorte', 'movimentacoes', 'salario_medio', 'salario_mediano', 'salarios_validos', 'n_referencia', 'remuneracao_relativa_pct'])
    st.caption(f'Denominadores das participações: {numero(detalhe.admissoes.sum())} admissões e {numero(detalhe.desligamentos.sum())} desligamentos no recorte.')
    mostrar_tabela(agregar(detalhe, ['cbo', 'descricao_cbo', 'macrofamilia']).sort_values('movimentacoes', ascending=False),
                   ['cbo', 'descricao_cbo', 'macrofamilia', 'admissoes', 'desligamentos', 'movimentacoes'])
    st.caption('As macrofamílias resultam de regras semânticas elaboradas com IA, sem revisão individual. Classificações genéricas e pendentes exigem validação.')

else:
    st.subheader('Síntese executiva do recorte')
    total = agregar(recorte, []).iloc[0]
    mun = municipios(estado, recorte).sort_values('saldo', ascending=False)
    alertas = sinais(estado, recorte).query('sinal_retencao').sort_values('movimentacoes', ascending=False)
    st.write(f"No período, o recorte registrou **{numero(total.admissoes)} admissões**, **{numero(total.desligamentos)} desligamentos** e saldo de **{numero(total.saldo)}**.")
    if not mun.empty:
        r = mun.iloc[0]
        st.write(f"O maior saldo municipal do recorte é **{r.nome_municipio}**, com **{numero(r.saldo)}** e **{numero(r.saldo_10000, 1)} por 10 mil habitantes**; a população estimada é {numero(r.populacao_estimada_2026)}.")
    if alertas.empty:
        st.write('Nenhum grupo atendeu à combinação de sinais de retenção adotada. Isso não elimina outras hipóteses de dificuldade.')
    else:
        for r in alertas.head(3).itertuples():
            st.markdown(f"**{r.nome_municipio} · {r.setor} · {r.macrofamilia_predominante}** — {numero(r.movimentacoes)} movimentações; {numero(r.pedidos)} pedidos em {numero(r.desligamentos)} desligamentos ({numero(r.pct_pedidos, 1)}%, contra {numero(r.pct_pedidos_sc, 1)}% em SC); remuneração relativa de {numero(r.remuneracao_relativa_pct, 1)}% (n={numero(r.n_referencia)}).")
            st.write(f"Ação proposta: investigar com empresas locais os motivos de saída e comparar faixas de remuneração das ocupações de **{r.macrofamilia_predominante}**; revisar o catálogo ocupacional e avaliar formação direcionada somente após validar necessidades de qualificação.")
    st.warning('São hipóteses, não causas comprovadas. O CAGED mede movimentações, não vagas abertas, estoque de empregos, requisitos da vaga nem trajetórias individuais. Salários são nominais; escolaridade é a observada nos trabalhadores.')
    st.caption('Roteiro sugerido: contexto e escala (30 s); expansão territorial e setorial (45 s); sinais combinados e limites (60 s); ações direcionadas e próximos passos (45 s).')
