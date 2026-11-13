"""Executa os três eixos e produz diagnóstico e metadados integrados."""
from datetime import datetime,timezone
import json
import pandas as pd
from comum import argumentos,dados_comuns,agregar,exportar,DICIONARIO,REFERENCIAS,CATALOGO
from cenarios import macrofamilia_predominante
import eixo1_territorial
import eixo2_socioeconomico
import eixo3_qualificacao

def diagnostico(df,saida):
    # Item 01: macrofamília fora da chave; informada como predominante no par município × setor.
    dimensoes=['codigo_ibge_7d','nome_municipio','codigo_regiao_imediata','regiao_imediata','cnae_divisao','setor']
    total=agregar(df,dimensoes).merge(macrofamilia_predominante(df,dimensoes),on=dimensoes,how='left',validate='one_to_one')
    eleg=total[total['movimentacoes'].ge(30)]
    limiar=eleg['movimentacoes'].quantile(.75)
    pct_estado=100*df['desligamentos_a_pedido'].sum()/df['desligamentos'].sum() if df['desligamentos'].sum() else float('nan')
    total['limiar_alta_movimentacao'] = limiar
    total['pct_desligamentos_a_pedido_estado'] = pct_estado
    total['alta_movimentacao']=total['movimentacoes'].ge(30)&total['movimentacoes'].ge(limiar)
    total['expansao']=total['movimentacoes'].ge(30)&total['saldo'].gt(0)
    total['retracao']=total['movimentacoes'].ge(30)&total['saldo'].lt(0)
    total['hipotese_investigar_retencao']=total['alta_movimentacao'] & total['pct_desligamentos_a_pedido_desligamentos_grupo'].gt(pct_estado) & total['n_admitidos_com_referencia'].ge(30) & total['remuneracao_relativa_mediana'].lt(1)
    mensal=agregar(df,['competencia']+dimensoes)
    exportar({'diagnostico_integrado':total,'diagnostico_integrado_mensal':mensal},saida/'integrado')
    return total

def documentar(df,auditoria,territorial,integrado,saida):
    layout=pd.read_excel(DICIONARIO,sheet_name='Layout',header=1,dtype=str).iloc[:,:3]
    layout.columns=['coluna','significado','codigo_dicionario']
    extras={
      'nome_municipio':'Nome do município IBGE','codigo_ibge_7d':'Código IBGE municipal com dígito verificador',
      'area_territorial_km2':'Área territorial municipal em 2025 (km²)','populacao_censo_2022':'População do censo de 2022',
      'densidade_demografica_2022':'Densidade demográfica do censo de 2022','populacao_estimada_2026':'População estimada em 2026',
      'taxa_escolarizacao_2022':'Taxa de escolarização de 6 a 14 anos em 2022','idhm_2010':'Índice de desenvolvimento humano municipal de 2010',
      'pib_per_capita_2023':'PIB municipal per capita de 2023','codigo_municipio_6d':'Código municipal IBGE sem dígito verificador'}
    tipos=pd.DataFrame([{'coluna':k,'tipo_observado':v} for k,v in auditoria['tipos_colunas'].items()])
    layout=pd.concat([layout,pd.DataFrame([{'coluna':k,'significado':v} for k,v in extras.items()])],ignore_index=True)
    layout=tipos.merge(layout,on='coluna',how='left',validate='one_to_one')
    exportar({'colunas_entrada':layout},saida)
    fontes=json.loads((REFERENCIAS/'fontes.json').read_text(encoding='utf-8'))
    metadados={'gerado_em_utc':datetime.now(timezone.utc).isoformat(),'auditoria':auditoria,'fontes_complementares':fontes,
      'catalogo_classificacao':str(CATALOGO),'salario_minimo':{'2024':1412,'2025':1518,'2026':1621},
      'metodo_classificacao':'Regras semânticas elaboradas por IA e aplicadas automaticamente; sem revisão individual.',
      'denominadores':{'pct_admissoes_total_sc':'admissões em SC no período correspondente','pct_desligamentos_total_sc':'desligamentos em SC no período correspondente',
       'pct_movimentacoes_total_sc':'admissões e desligamentos em SC no período correspondente','percentual_grupo_tipo_mov':'total do mesmo grupo e tipo de movimentação',
       'pct_desligamentos_a_pedido_desligamentos_grupo':'desligamentos do grupo','pct_salarios_validos_movimentacoes_grupo':'movimentações do grupo',
       'remuneracao_relativa_pct_referencia':'mediana estadual de admitidos da mesma escolaridade e competência',
       'saldo_por_10000_habitantes':'população municipal estimada em 2026'},
      'limitacoes':'Microdados não identificados: não permitem identificar vínculos duplicados, vagas abertas, duração de contratação, estoque nem requisitos de escolaridade.'}
    (saida/'metadados.json').write_text(json.dumps(metadados,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    mun=territorial['municipios']; setores=territorial['setores_divisao']; alertas=integrado[integrado['hipotese_investigar_retencao']].sort_values('movimentacoes',ascending=False)
    def lista(tabela, coluna, nome):
        return '\n'.join(f"- {row[nome]}: saldo {int(row['saldo']):+d}; {int(row['admissoes']):,} admissões ({row['pct_admissoes_total_sc']:.2f}% de SC) e {int(row['desligamentos']):,} desligamentos ({row['pct_desligamentos_total_sc']:.2f}% de SC)." for _,row in tabela.sort_values(coluna,ascending=False).head(5).iterrows())
    resumo_alertas='\n'.join(f"- {r['nome_municipio']} / {r['setor']} (macrofamília predominante: {r['macrofamilia_predominante']}, {r['pct_macrofamilia_predominante']:.0f}%): {int(r['movimentacoes'])} movimentações ({r['pct_movimentacoes_total_sc']:.3f}% de SC); {int(r['desligamentos_a_pedido'])} pedidos em {int(r['desligamentos'])} desligamentos ({r['pct_desligamentos_a_pedido_desligamentos_grupo']:.1f}%); remuneração mediana relativa de {r['remuneracao_relativa_pct_referencia']:.1f}% da referência estadual." for _,r in alertas.head(10).iterrows()) or 'Nenhuma combinação atingiu simultaneamente os critérios adotados.'
    n=len(df); a=int(df['admissoes'].sum()); d=int(df['desligamentos'].sum())
    relatorio=f'''# Diagnóstico do emprego industrial catarinense

Período: {auditoria['inicio']} a {auditoria['fim']} por competência da movimentação. Foram registradas {n:,} movimentações: {a:,} admissões ({100*a/n:.2f}% do total) e {d:,} desligamentos ({100*d/n:.2f}%); saldo de {a-d:+,}.

## Municípios com maiores saldos

{lista(mun,'saldo','nome_municipio')}

## Divisões CNAE com maiores saldos

{lista(setores,'saldo','setor')}

## Combinações que merecem investigação

{resumo_alertas}

O sinal exige ao menos 30 movimentações, volume no quartil superior, participação de pedidos de desligamento maior que a estadual e remuneração relativa inferior à mediana estadual comparável, com pelo menos 30 salários admitidos válidos. São hipóteses para investigação, não prova de escassez ou dificuldade de contratação.

## Método e limites

Saldo = admissões − desligamentos; movimentação = admissões + desligamentos; saldo por 10.000 habitantes = saldo / população municipal estimada em 2026 × 10.000. Percentuais estaduais usam o total do mesmo tipo e período em SC; distribuição de perfil usa o total do grupo e tipo de movimentação. Remuneração relativa usa como referência a mediana de admitidos da mesma escolaridade e competência, com pelo menos 30 salários válidos. Os valores são nominais, sem correção inflacionária.

Estatísticas salariais incluem apenas valores de 0,3 a 150 salários mínimos da competência e indicadores de intermitência iguais a zero. No período, {auditoria['salarios']['validos']:,} salários são elegíveis de {n:,} movimentações ({100*auditoria['salarios']['validos']/n:.2f}%). Os motivos de exclusão podem se sobrepor; a auditoria informa os totais e a exclusão única.

Foram preservadas {auditoria['repeticoes_identicas_excedentes']:,} repetições idênticas na base completa, pois registros anônimos iguais podem corresponder a vínculos distintos. Foram identificadas {auditoria['linhas_antes_periodo']:,} movimentações anteriores ao período principal.

A classificação ocupacional usa regras semânticas elaboradas por IA, aplicadas automaticamente a títulos CBO; os casos genéricos e pendentes exigem revisão. Não há revisão individual das classificações. A escolaridade é a observada entre trabalhadores; não comprova requisitos da vaga. O CAGED disponível não informa vagas abertas, tempo de preenchimento, estoque de empregos nem trajetórias de pessoas. Portanto, nenhuma métrica isolada prova apagão de mão de obra, causalidade ou dificuldade de contratação.
'''
    (saida/'relatorio.md').write_text(relatorio,encoding='utf-8')

def main():
    args=argumentos(); df,auditoria=dados_comuns(args)
    territorial=eixo1_territorial.analisar(df,args.saida)
    eixo2_socioeconomico.analisar(df,args.saida)
    eixo3_qualificacao.analisar(df,args.saida)
    integrado=diagnostico(df,args.saida)
    documentar(df,auditoria,territorial,integrado,args.saida)
    print(f'Resultados em {args.saida.resolve()} | {len(df):,} movimentações')

if __name__=='__main__': main()
