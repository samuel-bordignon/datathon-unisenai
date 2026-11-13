"""Painel do pitch de 3 minutos: emprego industrial em SC pelo Novo CAGED.

Quatro abas, uma por bloco do pitch: territorial e setorial (~50 s), perfil e
remuneração (~50 s), qualificação e IA (~50 s) e diagnóstico e ações (~30 s).
Todos os números são calculados sobre o recorte dos filtros da barra lateral.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / 'src' / 'analises'))
sys.path.insert(0, str(RAIZ / 'src'))
from ia import gemini
from ia.contexto import PROMPT_HIPOTESES, SISTEMA, detalhar_pergunta, montar_contexto, serializar
from cenarios import (agregar, cbos_deficit, desagio_escolaridade, divergente, evolucao,
                      municipios, sinais)
from comum import FAIXAS_ETARIAS, MOTIVOS, ORDEM_NIVEIS, ROTULOS_ESCOLARIDADE, SEM_IDADE
from mapa import orientar_malha

BASE = RAIZ / 'database' / 'resultados' / 'dashboard'
GEO = BASE / 'malha_sc.geojson'
AZUL, VERMELHO, VERDE = '#1f77b4', '#d62728', '#2ca02c'
CORES_MOTIVO = {'Admissão': AZUL, 'Pedido de demissão (40)': '#ff7f0e', 'Demissão pela empresa (31)': VERMELHO,
                'Fim de contrato (43/45)': '#9467bd', 'Outros desligamentos': '#7f7f7f'}
CORES_SENTIDO = {'Maiores saldos': AZUL, 'Menores saldos': VERMELHO}
LIMITES = ('O CAGED mede movimentações (fluxos), não vagas abertas, estoque de empregos nem requisitos da vaga. '
           'A escolaridade é a observada no trabalhador. Salários são nominais. Os resultados indicam hipóteses, não causas comprovadas.')
st.set_page_config(page_title='Indústria SC | Raio-X do emprego', page_icon='📊', layout='wide')


@st.cache_data(show_spinner='Carregando dados preparados...')
def carregar(caminho, modificacao):
    return pd.read_parquet(caminho)


@st.cache_data
def carregar_geo(caminho, modificacao):
    return orientar_malha(json.loads(Path(caminho).read_text(encoding='utf-8')))


def numero(valor, casas=0):
    if pd.isna(valor):
        return 'n/d'
    return f'{valor:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def sinal(valor):
    return ('+' if valor > 0 else '') + numero(valor)


def pct(valor, casas=1):
    return f'{numero(valor, casas)}%'


def mostrar(fig, altura=None):
    if altura:
        fig.update_layout(height=altura)
    fig.update_layout(template='plotly_white', margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, width='stretch')


def barras_divergentes(tabela, rotulo, titulo):
    dados = divergente(tabela, 'saldo')
    if dados.empty:
        st.info('Sem saldos positivos ou negativos neste recorte.')
        return
    fig = px.bar(dados, x='saldo', y=rotulo, orientation='h', color='sentido', color_discrete_map=CORES_SENTIDO,
                 text=dados.saldo.map(sinal), title=titulo, hover_data=['admissoes', 'desligamentos'],
                 labels={'saldo': 'Saldo (admissões − desligamentos)', rotulo: '', 'sentido': ''})
    fig.update_yaxes(categoryorder='array', categoryarray=dados[rotulo].tolist())
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.add_vline(x=0, line_color='black', line_width=1)
    mostrar(fig, 430)


def fluxo_por_motivo(df, dimensao, ordem, titulo, modo, rotulos=None):
    """Barras horizontais: admissões ao lado dos desligamentos empilhados pelos 4 motivos."""
    tabela = df.groupby([dimensao, 'motivo_movimentacao'], observed=True).size().rename('quantidade').reset_index()
    tabela['motivo_movimentacao'] = tabela.motivo_movimentacao.astype(str)
    tabela['fluxo'] = tabela.motivo_movimentacao.eq('Admissão').map({True: 'Admissões', False: 'Desligamentos'})
    if modo == 'Participação no fluxo do recorte (%)':
        tabela['valor'] = 100 * tabela.quantidade / tabela.groupby('fluxo').quantidade.transform('sum')
    elif modo == 'Composição dentro de cada grupo (%)':
        tabela['valor'] = 100 * tabela.quantidade / tabela.groupby([dimensao, 'fluxo'], observed=True).quantidade.transform('sum')
    else:
        tabela['valor'] = tabela.quantidade
    ordem = [c for c in ordem if c in set(tabela[dimensao].astype(str))]
    nomes = rotulos or {}
    eixo = [nomes.get(c, c) for c in ordem]
    fig = go.Figure()
    base = pd.Series(0.0, index=ordem)
    for motivo in MOTIVOS:
        parte = tabela[tabela.motivo_movimentacao.eq(motivo)].set_index(tabela[tabela.motivo_movimentacao.eq(motivo)][dimensao].astype(str))
        valores = parte.valor.reindex(ordem).fillna(0)
        qtd = parte.quantidade.reindex(ordem).fillna(0)
        grupo = 'adm' if motivo == 'Admissão' else 'des'
        fig.add_trace(go.Bar(y=eixo, x=valores, base=None if grupo == 'adm' else base.values, orientation='h',
            name=motivo, marker_color=CORES_MOTIVO[motivo], offsetgroup=grupo, legendgroup=grupo,
            customdata=qtd.values, hovertemplate=f'{motivo}<br>%{{y}}<br>Valor: %{{x:,.1f}}<br>Quantidade: %{{customdata:,.0f}}<extra></extra>'))
        if grupo == 'des':
            base = base + valores
    unidade = 'Quantidade' if modo == 'Quantidade' else '%'
    fig.update_layout(barmode='group', title=titulo, xaxis_title=unidade, legend_title='',
                      legend=dict(orientation='h', y=-0.12))
    fig.update_yaxes(categoryorder='array', categoryarray=eixo, autorange='reversed')
    mostrar(fig, max(380, 42 * len(ordem) + 140))


@st.cache_data(show_spinner=False, ttl=3600)
def hipoteses_ia(contexto, modelo, _chave):
    """Uma chamada por recorte e modelo; a chave fica fora do hash do cache."""
    return gemini.gerar(PROMPT_HIPOTESES + contexto, _chave, modelo, sistema=SISTEMA, json_saida=True)


def secao_ia(estado, recorte, escopo):
    st.markdown('#### Hipóteses e perguntas com IA (Google Gemini)')
    chave, modelo = gemini.configuracao(st.secrets)
    if not chave:
        st.info('IA desativada: configure `GEMINI_API_KEY` em `.streamlit/secrets.toml` (veja `.streamlit/secrets.toml.example`) '
                'ou na variável de ambiente `GEMINI_API_KEY` e reinicie o painel.')
        return
    contexto = serializar(montar_contexto(estado, recorte, escopo))
    st.caption(f'Modelo `{modelo}`. O Gemini recebe só tabelas agregadas deste recorte ({numero(len(contexto))} caracteres), nunca os microdados. '
               'Conteúdo gerado por IA: confira cada número nos gráficos.')
    if st.button('Gerar hipóteses com IA', type='primary'):
        st.session_state['hipoteses'] = contexto
    if st.session_state.get('hipoteses') == contexto:
        try:
            with st.spinner('Consultando o Gemini...'):
                bruto = hipoteses_ia(contexto, modelo, chave)
        except gemini.ErroIA as erro:
            st.session_state.pop('hipoteses', None)  # evita repetir a chamada com erro a cada interação
            st.error(str(erro))
        else:
            try:
                resposta = json.loads(bruto.strip().removeprefix('```json').removesuffix('```'))
            except json.JSONDecodeError:
                st.markdown(bruto)
            else:
                colunas = st.columns(min(3, max(1, len(resposta.get('hipoteses', [])))))
                for i, h in enumerate(resposta.get('hipoteses', [])):
                    with colunas[i % len(colunas)].container(border=True):
                        st.markdown(f"**{h.get('titulo', '')}**")
                        st.markdown(f"*Evidência:* {h.get('evidencia', '')}")
                        st.markdown(f"*Macrofamília:* {h.get('macrofamilia', '')}")
                        st.markdown(f"*Recomendação:* {h.get('recomendacao', '')}")
                if resposta.get('limites'):
                    st.caption('Limites apontados pela IA: ' + ' '.join(resposta['limites']))
    with st.expander('Conversar com a IA sobre este recorte'):
        if st.session_state.get('chat_contexto') != contexto:
            st.session_state['chat_contexto'], st.session_state['chat'] = contexto, []
        for msg in st.session_state['chat']:
            with st.chat_message('user' if msg['papel'] == 'user' else 'assistant'):
                st.markdown(msg['texto'])
        pergunta = st.chat_input('Ex.: Por que Concórdia aparece como polo de retenção?')
        if pergunta:
            historico = st.session_state['chat'][-6:]
            extra = detalhar_pergunta(estado, recorte, pergunta, historico)
            ctx_chat = contexto if not extra else f'{contexto}\nDETALHES_DA_PERGUNTA:\n{serializar(extra)}'
            with st.chat_message('user'):
                st.markdown(pergunta)
            with st.chat_message('assistant'):
                try:
                    with st.spinner('Consultando o Gemini...'):
                        texto = gemini.gerar(pergunta, chave, modelo, historico=historico,
                                             sistema=SISTEMA + '\nCONTEXTO:\n' + ctx_chat)
                except gemini.ErroIA as erro:
                    st.error(str(erro))
                    return
                st.markdown(texto)
            st.session_state['chat'] += [{'papel': 'user', 'texto': pergunta}, {'papel': 'model', 'texto': texto}]


def tabela(df, colunas, nomes):
    st.dataframe(df[[c for c in colunas if c in df.columns]].rename(columns=nomes), hide_index=True, width='stretch')


if not (BASE / 'movimentacoes.parquet').exists():
    st.title('Indústria SC | Raio-X do emprego')
    st.warning('A base do painel ainda não foi preparada. Execute: `python src/analises/preparar_dashboard.py`')
    st.stop()

df = carregar(str(BASE / 'movimentacoes.parquet'), (BASE / 'movimentacoes.parquet').stat().st_mtime_ns)
meta = json.loads((BASE / 'metadados.json').read_text(encoding='utf-8'))
st.title('Indústria SC | Raio-X do emprego industrial')
st.caption('Novo CAGED · admissões e desligamentos na indústria catarinense · hipóteses para orientar decisões')
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
    st.caption('Sem seleção, todos os valores entram. Limiares (quartis, % de pedidos de SC) usam sempre o estado no período.')
recorte = territorio
if cidades:
    recorte = recorte[recorte.nome_municipio.isin(cidades)]
if setores:
    recorte = recorte[recorte.setor.isin(setores)]
completo = not (regioes or cidades or setores) and (inicio, fim) == (competencias[0], competencias[-1])
escopo = 'SC, período completo' if completo else 'recorte filtrado'
st.caption(f'Período {str(inicio)[4:]}/{str(inicio)[:4]} a {str(fim)[4:]}/{str(fim)[:4]} · {numero(len(recorte))} movimentações ({escopo}) · base gerada em {meta["gerado_em_utc"][:10]}')
if recorte.empty:
    st.warning('Não há movimentações para a combinação de filtros selecionada.')
    st.stop()

ABAS = ['1. Territorial e setorial', '2. Perfil e remuneração', '3. Qualificação e IA', '4. Diagnóstico e ações']
pagina = st.radio('Navegação', ABAS, horizontal=True, label_visibility='collapsed')
total = agregar(recorte, []).iloc[0]
mun = municipios(estado, recorte)

if pagina == ABAS[0]:
    st.subheader('Onde o emprego industrial cresce e onde encolhe?')
    cols = st.columns(4)
    cols[0].metric('Admissões', numero(total.admissoes))
    cols[1].metric('Desligamentos', numero(total.desligamentos))
    cols[2].metric('Saldo', sinal(total.saldo))
    cols[3].metric('Pedidos de demissão', pct(total.pct_pedidos), help='Desligamentos a pedido do trabalhador (código 40) sobre o total de desligamentos.')

    indicador = st.radio('Indicador do mapa', ['Saldo absoluto', 'Saldo por 10 mil habitantes'], horizontal=True)
    coluna = 'saldo' if indicador == 'Saldo absoluto' else 'saldo_10000'
    if GEO.exists():
        geo = carregar_geo(str(GEO), GEO.stat().st_mtime_ns)
        limite = mun[coluna].abs().quantile(.98) or 1
        fig = px.choropleth(mun, geojson=geo, locations='codigo_ibge_7d', featureidkey='properties.codarea', color=coluna,
                            hover_name='nome_municipio', hover_data={'admissoes': ':,', 'desligamentos': ':,', 'saldo': ':,', 'saldo_10000': ':.1f', 'codigo_ibge_7d': False},
                            color_continuous_scale='RdBu', range_color=(-limite, limite),
                            labels={'saldo': 'Saldo', 'saldo_10000': 'Saldo/10 mil hab.'}, title=f'{indicador} por município')
        fig.update_geos(fitbounds='locations', visible=False)
        mostrar(fig, 560)
        if coluna == 'saldo_10000':
            st.caption('Saldo por 10 mil habitantes usa a população estimada de 2026. Em municípios pequenos, uma única empresa muda muito o valor. Escala limitada ao percentil 98 para não esconder o restante do mapa.')
    else:
        st.warning('Malha municipal não encontrada. Execute `python src/analises/obter_referencias.py`.')

    mensal = evolucao(recorte)
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Bar(x=mensal.competencia.astype(str), y=mensal.saldo, name='Saldo do mês',
                         marker_color=[AZUL if v >= 0 else VERMELHO for v in mensal.saldo],
                         hovertemplate='%{x}<br>Saldo: %{y:,}<extra></extra>'), secondary_y=False)
    fig.add_trace(go.Scatter(x=mensal.competencia.astype(str), y=mensal.saldo_acumulado, name='Saldo acumulado',
                             mode='lines+markers', line=dict(color=VERDE, width=3)), secondary_y=True)
    fig.update_layout(title='Saldo mensal (azul positivo, vermelho negativo) e saldo acumulado', legend=dict(orientation='h', y=-0.15))
    fig.update_xaxes(type='category', title='Competência')
    fig.update_yaxes(title_text='Saldo do mês', secondary_y=False)
    fig.update_yaxes(title_text='Saldo acumulado', secondary_y=True, showgrid=False)
    mostrar(fig, 420)

    a, b = st.columns(2)
    with a:
        barras_divergentes(mun, 'nome_municipio', 'Municípios: 5 maiores e 5 menores saldos')
    with b:
        setores_tab = agregar(recorte, ['setor'])
        setores_tab['setor'] = setores_tab.setor.str.capitalize().str.slice(0, 55)
        barras_divergentes(setores_tab, 'setor', 'Setores CNAE: 5 maiores e 5 menores saldos')

elif pagina == ABAS[1]:
    st.subheader('Quem entra, quem sai e quanto ganha?')
    modo = st.radio('Escala dos gráficos de perfil', ['Participação no fluxo do recorte (%)', 'Composição dentro de cada grupo (%)', 'Quantidade'],
                    horizontal=True, help='Participação: compara o perfil de quem entra com o de quem sai. Composição: mostra, dentro de cada grupo, a divisão entre os motivos.')
    a, b = st.columns(2)
    with a:
        fluxo_por_motivo(recorte, 'escolaridade', ROTULOS_ESCOLARIDADE, 'Escolaridade (ordem acadêmica): admissões × desligamentos por motivo', modo)
    with b:
        fluxo_por_motivo(recorte, 'faixa_etaria', FAIXAS_ETARIAS + [SEM_IDADE], 'Faixa etária: admissões × desligamentos por motivo', modo)
    idade = agregar(recorte, ['faixa_etaria'])
    idade = idade[idade.desligamentos.gt(0)]
    if not idade.empty:
        jovem = idade[idade.faixa_etaria.astype(str).isin(['18 a 24 anos', '25 a 34 anos'])]
        madura = idade[idade.faixa_etaria.astype(str).isin(['45 a 54 anos', '55 anos ou mais'])]
        def taxa(t, col):
            return 100 * t[col].sum() / t.desligamentos.sum() if t.desligamentos.sum() else float('nan')
        st.caption(f'Pedidos de demissão sobre desligamentos: {pct(taxa(jovem, "pedidos"))} entre 18 e 34 anos e {pct(taxa(madura, "pedidos"))} a partir de 45 anos. '
                   f'Demissões pela empresa: {pct(taxa(jovem, "demissoes_empresa"))} e {pct(taxa(madura, "demissoes_empresa"))}, respectivamente ({escopo}).')

    longo, largo = desagio_escolaridade(recorte)
    if longo.empty:
        st.info('Sem salários válidos neste recorte.')
    else:
        ordem = [c for c in ROTULOS_ESCOLARIDADE if c in set(longo.escolaridade.astype(str))]
        longo['escolaridade'] = longo.escolaridade.astype(str)
        longo['amostra'] = longo.suficiente.map({True: 'n ≥ 30', False: 'amostra insuficiente (n < 30)'})
        fig = px.bar(longo, x='escolaridade', y='mediana', color='grupo', barmode='group',
                     category_orders={'escolaridade': ordem, 'grupo': ['Admitidos', 'Pedido de demissão (40)', 'Demissão pela empresa (31)']},
                     color_discrete_map={'Admitidos': AZUL, 'Pedido de demissão (40)': CORES_MOTIVO['Pedido de demissão (40)'], 'Demissão pela empresa (31)': VERMELHO},
                     hover_data={'n': ':,', 'media': ':,.0f', 'amostra': True}, labels={'mediana': 'Salário mediano (R$)', 'escolaridade': '', 'grupo': ''},
                     title='Salário mediano por escolaridade: entrada × saída')
        coluna = 'desagio_mediana_Demissão pela empresa (31)'
        if coluna in largo.columns:
            for esc, valor in zip(largo.escolaridade.astype(str), largo[coluna]):
                topo = longo[longo.escolaridade.eq(esc)].mediana.max()
                if pd.notna(valor):
                    fig.add_annotation(x=esc, y=topo, text=pct(valor, 0), showarrow=False, yshift=12, font=dict(size=11, color=VERMELHO))
        fig.update_layout(legend=dict(orientation='h', y=-0.3))
        mostrar(fig, 480)
        adm = recorte[recorte.admissoes.eq(1)].salario_valido.median()
        emp = recorte[recorte.demissoes_empresa.eq(1)].salario_valido.median()
        ped = recorte[recorte.desligamentos_a_pedido.eq(1)].salario_valido.median()
        c1, c2, c3 = st.columns(3)
        c1.metric('Mediana dos admitidos', f'R$ {numero(adm, 2)}')
        c2.metric('Mediana dos pedidos de demissão', f'R$ {numero(ped, 2)}', f'{numero(100 * (adm - ped) / ped, 1)}% para quem entra' if ped else None, delta_color='off')
        c3.metric('Mediana das demissões pela empresa', f'R$ {numero(emp, 2)}', f'{numero(100 * (adm - emp) / emp, 1)}% para quem entra' if emp else None, delta_color='off')
        st.info('Em vermelho, acima das barras: deságio pela mediana entre quem é admitido e quem foi demitido pela empresa na mesma escolaridade. '
                'A diferença cresce com a escolaridade. Ela é compatível com compressão salarial ou com o maior tempo de casa de quem sai; o CAGED não separa as duas explicações. '
                'Quem pede demissão ganha quase o mesmo que quem entra, o que sugere pouco ganho salarial com a permanência.')

elif pagina == ABAS[2]:
    st.subheader('As saídas se concentram na base operacional ou nas funções técnicas?')
    a, b = st.columns([1, 2])
    with a:
        detalhe = st.radio('Agrupar por', ['Nível de atuação (grande grupo CBO)', 'Macrofamília (IA)'])
    with b:
        modo = st.radio('Escala', ['Quantidade', 'Composição dentro de cada grupo (%)', 'Participação no fluxo do recorte (%)'], horizontal=True)
    if detalhe.startswith('Nível'):
        fluxo_por_motivo(recorte, 'nivel_atuacao', ORDEM_NIVEIS, 'Nível de atuação: admissões × desligamentos por motivo', modo)
        st.caption('Nível pelo primeiro dígito da CBO 2002 (MTE): grupos 1 a 3 = dirigentes, profissionais das ciências e técnicos; 4 a 6 = serviços administrativos, comércio e agropecuária; 7 a 9 = produção, operação e manutenção.')
    else:
        fam = agregar(recorte, ['macrofamilia']).sort_values('movimentacoes', ascending=False)
        fluxo_por_motivo(recorte, 'macrofamilia', fam.macrofamilia.tolist(), 'Macrofamílias (IA): admissões × desligamentos por motivo', modo)
    deficit = cbos_deficit(recorte, 10)
    if deficit.empty:
        st.info('Nenhuma ocupação com mais desligamentos que admissões neste recorte.')
    else:
        siglas = {'Operacional de base': 'Base', 'Apoio administrativo e serviços': 'Apoio', 'Gestão, engenharia e técnicos': 'Técnico/gestão'}
        rotulos = {r.descricao_cbo: f'{r.descricao_cbo[:45]} [{siglas.get(r.nivel_atuacao, "?")}] · déficit {numero(r.deficit)}' for r in deficit.itertuples()}
        fluxo_por_motivo(recorte[recorte.descricao_cbo.isin(deficit.descricao_cbo)], 'descricao_cbo', deficit.descricao_cbo.tolist(),
                         'Ocupações (CBO) com maior déficit: desligamentos − admissões', 'Quantidade', rotulos)
    resumo = BASE.parent / 'ia' / 'validacao_resumo.json'
    texto_ia = 'Macrofamílias: 19 grupos definidos por regras semânticas elaboradas com IA a partir dos títulos das CBOs.'
    if resumo.exists():
        r = json.loads(resumo.read_text(encoding='utf-8'))
        texto_ia += f" Validação com {r['modelo']}: concordância de {pct(r['concordancia_pct'])} das CBOs e {pct(r['concordancia_ponderada_pct'])} das movimentações."
    st.caption(texto_ia + ' O saldo negativo de gestão e engenharia pode refletir promoções internas, que o CAGED não registra como admissão.')

else:
    st.subheader('Diagnóstico e ações')
    st.markdown('> *Quais regiões e setores industriais de SC enfrentam apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?*')
    grupos = sinais(estado, recorte)
    alertas = grupos[grupos.sinal_retencao].sort_values('movimentacoes', ascending=False)
    ordenado = mun.sort_values('saldo', ascending=False)
    setores_tab = agregar(recorte, ['setor']).sort_values('saldo', ascending=False)
    cresce = ordenado[ordenado.saldo.gt(0)].head(3)
    encolhe = ordenado[ordenado.saldo.lt(0)].tail(3).iloc[::-1]
    adm = recorte[recorte.admissoes.eq(1)]
    medio = 100 * adm.escolaridade.astype(str).eq('Médio Completo').mean() if len(adm) else float('nan')
    m_adm = adm.salario_valido.median()
    m_emp = recorte[recorte.demissoes_empresa.eq(1)].salario_valido.median()
    m_ped = recorte[recorte.desligamentos_a_pedido.eq(1)].salario_valido.median()

    def lista_mun(t):
        return '; '.join(f'{r.nome_municipio} {sinal(r.saldo)} ({numero(r.saldo_10000, 0)}/10 mil hab.)' for r in t.itertuples()) or 'nenhum'

    def lista_setor(t):
        return '; '.join(f'{r.setor.capitalize()} {sinal(r.saldo)}' for r in t.itertuples()) or 'nenhum'

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('#### Expansão')
        st.markdown(f'**Municípios:** {lista_mun(cresce)}.\n\n**Setores:** {lista_setor(setores_tab[setores_tab.saldo.gt(0)].head(2))}.')
    with c2:
        st.markdown('#### Retração e retenção')
        st.markdown(f'**Municípios:** {lista_mun(encolhe)}.\n\n**Setores:** {lista_setor(setores_tab[setores_tab.saldo.lt(0)].tail(2).iloc[::-1])}.\n\n'
                    f'**Polos com sinal de retenção:** {len(alertas)} pares município × setor.')
    with c3:
        st.markdown('#### Renda e escolaridade')
        st.markdown(f'**{pct(medio)}** das admissões são de Ensino Médio Completo. **{pct(total.pct_pedidos)}** dos desligamentos são pedidos do trabalhador.\n\n'
                    f'Mediana de quem pede demissão: R$ {numero(m_ped, 0)}, contra R$ {numero(m_adm, 0)} de quem entra. '
                    f'Quem é demitido pela empresa ganhava R$ {numero(m_emp, 0)}; quem entra recebe {pct(100 * (m_emp - m_adm) / m_emp if m_emp else float("nan"))} a menos.')
    st.caption(f'Valores: {escopo}. Medianas.')

    st.markdown('#### Polos críticos (um registro por município × setor)')
    st.caption('Sinal de retenção: ao menos 30 movimentações e volume no quartil superior de SC; % de pedidos acima da média de SC; remuneração dos admitidos abaixo da mediana estadual da mesma escolaridade (n ≥ 30).')
    if alertas.empty:
        st.info('Nenhum par município × setor atende a todos os critérios neste recorte.')
    else:
        tabela(alertas.head(15), ['nome_municipio', 'setor', 'macrofamilia_predominante', 'pct_macrofamilia_predominante', 'movimentacoes', 'saldo', 'pct_pedidos', 'remuneracao_relativa_pct'],
               {'nome_municipio': 'Município', 'setor': 'Setor CNAE', 'macrofamilia_predominante': 'Macrofamília predominante', 'pct_macrofamilia_predominante': '% da macrofamília',
                'movimentacoes': 'Movimentações', 'saldo': 'Saldo', 'pct_pedidos': '% pedidos', 'remuneracao_relativa_pct': 'Remuneração relativa (%)'})

    familias = alertas.macrofamilia_predominante.value_counts().head(3).index.tolist() if not alertas.empty else []
    deficit = cbos_deficit(recorte, 10)
    fam_deficit = deficit.macrofamilia.value_counts().head(3).index.tolist() if 'macrofamilia' in deficit else []
    expansao = agregar(recorte, ['nome_municipio', 'macrofamilia']).sort_values('saldo', ascending=False).head(3)
    st.markdown('#### Recomendações')
    st.markdown(
        f"1. **Degraus salariais na base operacional** ({', '.join(familias) or 'macrofamílias dos polos críticos'}): reajustes previstos aos 6, 12 e 24 meses, "
        f"para que a permanência renda mais do que a troca de empresa. Indicador: queda do % de pedidos (hoje {pct(total.pct_pedidos)}).\n"
        f"2. **Trilhas SENAI de formação no trabalho** nas macrofamílias com maior déficit de ocupações ({', '.join(fam_deficit) or 'n/d'}), ligadas a bônus de retenção técnica.\n"
        f"3. **Atração de talentos regionais nos polos de expansão** ({'; '.join(f'{r.nome_municipio} · {r.macrofamilia} {sinal(r.saldo)}' for r in expansao.itertuples())}): "
        'parcerias entre FIESC, prefeituras e empresas para captar e qualificar trabalhadores antes que a demanda pressione salários e infraestrutura.')
    secao_ia(estado, recorte, escopo)
    st.warning('Premissas e limites: ' + LIMITES + ' Macrofamílias definidas por regras elaboradas com IA, sem revisão individual.')
