"""Leitura, enriquecimento e métricas compartilhadas pelos três eixos."""
from pathlib import Path
import argparse
import json
import hashlib
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / 'database/doc/Caged_Industrial_SC_Limpo_Unificado.csv'
SAIDA = RAIZ / 'database/resultados'
REFERENCIAS = RAIZ / 'database/doc/referencias_analises'
DICIONARIO = RAIZ / 'database/doc/Dicionario_de_dados.xlsx'
CATALOGO = Path(__file__).with_name('catalogo_cbos_ia.csv')
COLUNAS = ['competênciamov','município','seção','subclasse','saldomovimentação','cbo2002ocupação','graudeinstrução','idade','salário','indtrabintermitente','tipomovimentação','nome_municipio','codigo_ibge_7d','populacao_estimada_2026','indicadordeforadoprazo']
CODIGOS = {'município':'string','subclasse':'string','cbo2002ocupação':'string','codigo_ibge_7d':'string'}
MINIMOS = {2024:1412.0, 2025:1518.0, 2026:1621.0}

# Progressão acadêmica pelos códigos do CAGED: 80 (Pós-Graduação) vem antes de 10 (Mestrado).
ORDEM_ESCOLARIDADE = ['1','2','3','4','5','6','7','8','9','80','10','11','99']
ROTULOS_ESCOLARIDADE = ['Analfabeto','Até 5ª Incompleto','5ª Completo Fundamental','6ª a 9ª Fundamental',
    'Fundamental Completo','Médio Incompleto','Médio Completo','Superior Incompleto','Superior Completo',
    'Pós-Graduação completa','Mestrado','Doutorado','Não Identificado']
FAIXAS_ETARIAS = ['Até 17 anos','18 a 24 anos','25 a 34 anos','35 a 44 anos','45 a 54 anos','55 anos ou mais']
SEM_IDADE = 'Não informada'
MOTIVOS = ['Admissão','Pedido de demissão (40)','Demissão pela empresa (31)','Fim de contrato (43/45)','Outros desligamentos']
# Nível de atuação pelo grande grupo da CBO 2002 (primeiro dígito), classificação oficial do MTE.
NIVEIS_ATUACAO = {'1':'Gestão, engenharia e técnicos','2':'Gestão, engenharia e técnicos','3':'Gestão, engenharia e técnicos',
    '4':'Apoio administrativo e serviços','5':'Apoio administrativo e serviços','6':'Apoio administrativo e serviços',
    '7':'Operacional de base','8':'Operacional de base','9':'Operacional de base'}
ORDEM_NIVEIS = ['Operacional de base','Apoio administrativo e serviços','Gestão, engenharia e técnicos','Não classificado']


def ordenar_escolaridade(serie):
    """Categoria ordenada pela progressão acadêmica; rótulos desconhecidos vão ao fim."""
    extras = sorted(set(serie.dropna().astype(str)) - set(ROTULOS_ESCOLARIDADE))
    return pd.Categorical(serie.astype('object'), categories=ROTULOS_ESCOLARIDADE + extras, ordered=True)


def faixa_etaria(idade):
    """Faixas de idade fechadas à direita; idade ausente vira 'Não informada'."""
    faixa = pd.cut(pd.to_numeric(idade, errors='coerce'), [-float('inf'),17,24,34,44,54,float('inf')], labels=FAIXAS_ETARIAS)
    return pd.Categorical(faixa.astype('object').where(faixa.notna(), SEM_IDADE),
                          categories=FAIXAS_ETARIAS + [SEM_IDADE], ordered=True)


def classificar_motivos(saldo_mov, tipo_movimentacao):
    """Indicadores mutuamente exclusivos de motivo; os quatro somam os desligamentos."""
    deslig = saldo_mov.eq(-1)
    tipo = pd.to_numeric(tipo_movimentacao, errors='coerce')
    pedido = deslig & tipo.eq(40)
    empresa = deslig & tipo.eq(31)
    termino = deslig & tipo.isin([43, 45])
    outros = deslig & ~(pedido | empresa | termino)
    motivo = pd.Series(MOTIVOS[0], index=saldo_mov.index, dtype='object')
    for mascara, nome in zip([pedido, empresa, termino, outros], MOTIVOS[1:]):
        motivo = motivo.mask(mascara, nome)
    return pd.DataFrame({'desligamentos_a_pedido': pedido.astype('int8'), 'demissoes_empresa': empresa.astype('int8'),
        'terminos_contrato': termino.astype('int8'), 'outros_desligamentos': outros.astype('int8'),
        'motivo_movimentacao': pd.Categorical(motivo, categories=MOTIVOS, ordered=True)}, index=saldo_mov.index)


def nivel_atuacao(cbo):
    return cbo.astype('string').str[0].map(NIVEIS_ATUACAO).fillna('Não classificado').astype('object')

def argumentos():
    parser = argparse.ArgumentParser()
    parser.add_argument('--entrada', type=Path, default=ENTRADA)
    parser.add_argument('--inicio', type=int, default=202509)
    parser.add_argument('--fim', type=int, default=202608)
    parser.add_argument('--saida', type=Path, default=SAIDA)
    return parser.parse_args()

def hash_arquivo(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for bloco in iter(lambda: f.read(1024*1024), b''): h.update(bloco)
    return h.hexdigest()

def dicionario(aba):
    tabela = pd.read_excel(DICIONARIO, sheet_name=aba, dtype=str).iloc[:, :2].copy()
    tabela.columns = ['codigo','descricao']
    return tabela.dropna(subset=['codigo']).drop_duplicates('codigo')

def elegibilidade_salarial(salario, minimo, intermitente):
    """Retorna faixa válida e máscara final, sem excluir movimentações da base."""
    faixa = salario.ge(minimo * 0.3) & salario.le(minimo * 150)
    return faixa, faixa & intermitente.eq(0)

def carregar(args):
    if args.inicio > args.fim: raise ValueError('Competência inicial posterior à final')
    cabecalho = pd.read_csv(args.entrada, sep=';', encoding='utf-8', nrows=0)
    faltantes = set(COLUNAS) - set(cabecalho.columns)
    if faltantes: raise ValueError(f'Colunas obrigatórias ausentes: {sorted(faltantes)}')
    # Todas as 38 colunas são lidas para auditar repetições exatas.
    completo = pd.read_csv(args.entrada, sep=';', encoding='utf-8', dtype=CODIGOS, low_memory=False)
    tipos = completo.dtypes.astype(str).to_dict()
    duplicados = int(completo.duplicated().sum())
    competencia = pd.to_numeric(completo['competênciamov'], errors='coerce')
    valido = competencia.between(args.inicio,args.fim)
    auditoria = {'linhas_total':len(completo),'linhas_periodo':int(valido.sum()),
        'linhas_antes_periodo':int(competencia.lt(args.inicio).sum()), 'linhas_depois_periodo':int(competencia.gt(args.fim).sum()),
        'competencias_invalidas':int(competencia.isna().sum()),'repeticoes_identicas_excedentes':duplicados,
        'inicio':args.inicio,'fim':args.fim,'tipos_colunas':tipos,'sha256_entrada':hash_arquivo(args.entrada)}
    df = completo.loc[valido,COLUNAS].copy(); del completo
    if df.empty: raise ValueError('Nenhum registro no período selecionado')
    if not df['seção'].isin(list('BCDEF')).all(): raise ValueError('Há seções não industriais na entrada')
    if not df['saldomovimentação'].isin([-1,1]).all(): raise ValueError('Saldo de movimentação inválido')
    for coluna, largura in [('município',6),('subclasse',7),('cbo2002ocupação',6),('codigo_ibge_7d',7)]:
        df[coluna] = df[coluna].str.replace(r'\.0$', '', regex=True).str.zfill(largura)
    df.rename(columns={'competênciamov':'competencia','município':'codigo_municipio_6d','seção':'secao',
        'subclasse':'cnae_subclasse','saldomovimentação':'saldo_mov','cbo2002ocupação':'cbo',
        'graudeinstrução':'codigo_escolaridade','salário':'salario','tipomovimentação':'tipo_movimentacao'}, inplace=True)
    if not df['codigo_ibge_7d'].str.startswith('42').all(): raise ValueError('Existem municípios fora de SC')
    if not df['codigo_ibge_7d'].str[:6].eq(df['codigo_municipio_6d']).all(): raise ValueError('Chaves municipais incompatíveis')
    demo = df.groupby('codigo_ibge_7d',dropna=False)[['nome_municipio','populacao_estimada_2026']].nunique(dropna=False)
    if demo.gt(1).any(axis=None): raise ValueError('Dados demográficos divergentes para um município')
    df['cnae_divisao'] = df['cnae_subclasse'].str[:2]
    df['admissoes'] = df['saldo_mov'].eq(1).astype('int8')
    df['desligamentos'] = df['saldo_mov'].eq(-1).astype('int8')
    df = df.join(classificar_motivos(df['saldo_mov'], df['tipo_movimentacao']))
    df['faixa_etaria'] = faixa_etaria(df['idade'])
    df['nivel_atuacao'] = nivel_atuacao(df['cbo'])
    df['tipo_mov'] = df['saldo_mov'].map({1:'Admissão',-1:'Desligamento'})
    ano = df['competencia'].floordiv(100)
    minimo = ano.map(MINIMOS)
    if minimo.isna().any(): raise ValueError(f'Salário mínimo não configurado para anos: {sorted(ano[minimo.isna()].unique())}')
    salario = pd.to_numeric(df['salario'],errors='coerce')
    faixa_ok, elegivel = elegibilidade_salarial(salario, minimo, df['indtrabintermitente'])
    intermitencia_ok = df['indtrabintermitente'].eq(0)
    df['salario_valido'] = salario.where(elegivel)
    df['salario_em_minimos'] = (salario/minimo).where(elegivel)
    limites = [0,1,1.5,2,3,5,10,float('inf')]
    nomes = ['Até 1','>1 a 1,5','>1,5 a 2','>2 a 3','>3 a 5','>5 a 10','>10']
    df['faixa_salarial'] = pd.cut(df['salario_em_minimos'], limites, labels=nomes).astype('string').fillna('Inelegível ou ausente')
    auditoria['salarios'] = {'validos':int(elegivel.sum()),'ausentes':int(salario.isna().sum()),
        'fora_faixa_nao_ausente':int((salario.notna() & ~faixa_ok).sum()),
        'intermitentes_ou_desconhecidos':int((~intermitencia_ok).sum()),'exclusoes_unicas':int((~elegivel).sum())}
    educ = dicionario('graudeinstrução').rename(columns={'codigo':'codigo_escolaridade','descricao':'escolaridade'})
    df['codigo_escolaridade'] = df['codigo_escolaridade'].astype('string').str.replace(r'\.0$', '',regex=True)
    df = df.merge(educ,on='codigo_escolaridade',how='left',validate='many_to_one')
    df['escolaridade'] = ordenar_escolaridade(df['escolaridade'].fillna('Não Identificado'))
    df['superior_completo'] = df['codigo_escolaridade'].isin(['9','10','11','80']).astype('int8')
    mun = pd.json_normalize(json.loads((REFERENCIAS/'municipios.json').read_text(encoding='utf-8')))
    mun = mun[['id','regiao-imediata.id','regiao-imediata.nome']].rename(columns={'id':'codigo_ibge_7d','regiao-imediata.id':'codigo_regiao_imediata','regiao-imediata.nome':'regiao_imediata'})
    mun['codigo_ibge_7d'] = mun['codigo_ibge_7d'].astype('string').str.zfill(7)
    df = df.merge(mun, on='codigo_ibge_7d', how='left', validate='many_to_one')
    divisao = pd.read_json(REFERENCIAS/'cnae_divisoes.json',dtype={'id':str})[['id','descricao']].rename(columns={'id':'cnae_divisao','descricao':'setor'})
    divisao['cnae_divisao'] = divisao['cnae_divisao'].astype('string').str.zfill(2)
    df = df.merge(divisao,on='cnae_divisao',how='left',validate='many_to_one')
    sub = dicionario('subclasse').rename(columns={'codigo':'cnae_subclasse','descricao':'descricao_subclasse'})
    sub['cnae_subclasse'] = sub['cnae_subclasse'].str.zfill(7)
    df = df.merge(sub,on='cnae_subclasse',how='left',validate='many_to_one')
    cat = pd.read_csv(CATALOGO,sep=';',dtype={'cbo':'string'},encoding='utf-8-sig')
    if cat['cbo'].duplicated().any(): raise ValueError('CBO duplicada no catálogo de classificação')
    df = df.merge(cat,on='cbo',how='left',validate='many_to_one')
    for col in ['macrofamilia','funcao_profissional','descricao_cbo','justificativa']:
        df[col] = df[col].fillna('Pendente de classificação' if col != 'descricao_cbo' else 'Descrição não identificada')
    auditoria['referencias'] = {'municipios_sem_regiao':int(df['regiao_imediata'].isna().sum()),
        'movimentacoes_cbo_pendente':int(df['macrofamilia'].eq('Pendente de classificação').sum())}
    # Referência estadual por competência e escolaridade evita comparar composições distintas.
    adm = df['admissoes'].eq(1) & df['salario_valido'].notna()
    ref = df.loc[adm].groupby(['competencia','codigo_escolaridade'],dropna=False,observed=True)['salario_valido'].agg(mediana_estadual_escolaridade_mes='median', n_referencia_estadual='count').reset_index()
    df = df.merge(ref,on=['competencia','codigo_escolaridade'],how='left',validate='many_to_one')
    df['salario_relativo_referencia'] = (df['salario_valido']/df['mediana_estadual_escolaridade_mes']).where(adm & df['mediana_estadual_escolaridade_mes'].gt(0) & df['n_referencia_estadual'].ge(30))
    return df,auditoria

def agregar(df, chaves):
    g = df.groupby(chaves,dropna=False,observed=True)
    out = g.agg(admissoes=('admissoes','sum'), desligamentos=('desligamentos','sum'),
        desligamentos_a_pedido=('desligamentos_a_pedido','sum'), salarios_validos=('salario_valido','count'),
        salario_medio=('salario_valido','mean'), salario_mediano=('salario_valido','median'),
        remuneracao_relativa_mediana=('salario_relativo_referencia','median'), n_admitidos_com_referencia=('salario_relativo_referencia','count'),
        **{c:(c,'sum') for c in ['demissoes_empresa','terminos_contrato','outros_desligamentos'] if c in df.columns}).reset_index()
    out['movimentacoes'] = out['admissoes']+out['desligamentos']; out['saldo'] = out['admissoes']-out['desligamentos']
    if 'competencia' in chaves:
        totais = df.groupby('competencia',dropna=False,observed=True).agg(denominador_admissoes_sc=('admissoes','sum'),denominador_desligamentos_sc=('desligamentos','sum'),denominador_movimentacoes_sc=('saldo_mov','size')).reset_index()
        out = out.merge(totais,on='competencia',how='left',validate='many_to_one')
    else:
        out['denominador_admissoes_sc'] = df['admissoes'].sum()
        out['denominador_desligamentos_sc'] = df['desligamentos'].sum()
        out['denominador_movimentacoes_sc'] = len(df)
    for medida in ['admissoes','desligamentos','movimentacoes']:
        denominador = out[f'denominador_{medida}_sc'].replace(0,float('nan'))
        out[f'pct_{medida}_total_sc'] = 100*out[medida]/denominador
    out['pct_desligamentos_a_pedido_desligamentos_grupo'] = 100*out['desligamentos_a_pedido']/out['desligamentos'].replace(0,float('nan'))
    out['pct_salarios_validos_movimentacoes_grupo'] = 100*out['salarios_validos']/out['movimentacoes'].replace(0,float('nan'))
    out['remuneracao_relativa_pct_referencia'] = out['remuneracao_relativa_mediana']*100
    return out

def distribuicao(df, dimensoes, categoria):
    chaves = dimensoes + ['tipo_mov',categoria]
    resultado = df.groupby(chaves,dropna=False,observed=True).size().rename('quantidade').reset_index()
    denom = resultado.groupby(dimensoes+['tipo_mov'],dropna=False,observed=True)['quantidade'].transform('sum')
    resultado['denominador_total_grupo_tipo_mov'] = denom
    resultado['percentual_grupo_tipo_mov'] = resultado['quantidade'].div(denom.where(denom.ne(0))).mul(100)
    return resultado

def exportar(tabelas, pasta):
    pasta.mkdir(parents=True,exist_ok=True)
    for nome,tabela in tabelas.items(): tabela.to_csv(pasta/f'{nome}.csv',sep=';',encoding='utf-8-sig',index=False)

def dados_comuns(args):
    args.saida.mkdir(parents=True,exist_ok=True)
    df,auditoria = carregar(args)
    (args.saida/'auditoria.json').write_text(json.dumps(auditoria,ensure_ascii=False,indent=2),encoding='utf-8')
    return df,auditoria
