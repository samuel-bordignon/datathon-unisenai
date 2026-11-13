"""Eixo 2: escolaridade e remuneração dos trabalhadores movimentados."""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from comum import argumentos,dados_comuns,agregar,distribuicao,exportar

def salarios(df,chaves):
    tabela=agregar(df,chaves+['tipo_mov'])
    return tabela

def diferencas(df,chaves):
    base=salarios(df,chaves)
    adm=base[base['tipo_mov'].eq('Admissão')][chaves+['salario_medio','salario_mediano','salarios_validos']].rename(columns={'salario_medio':'media_admitidos','salario_mediano':'mediana_admitidos','salarios_validos':'n_admitidos_validos'})
    des=base[base['tipo_mov'].eq('Desligamento')][chaves+['salario_medio','salario_mediano','salarios_validos']].rename(columns={'salario_medio':'media_desligados','salario_mediano':'mediana_desligados','salarios_validos':'n_desligados_validos'})
    out=adm.merge(des,on=chaves,how='outer',validate='one_to_one')
    for medida in ['media','mediana']:
        out[f'diferenca_{medida}_reais']=out[f'{medida}_admitidos']-out[f'{medida}_desligados']
        out[f'diferenca_{medida}_pct_desligados']=out[f'diferenca_{medida}_reais'].div(out[f'{medida}_desligados'].where(out[f'{medida}_desligados'].ne(0))).mul(100)
    out['amostra_suficiente']=(out['n_admitidos_validos'].ge(30)&out['n_desligados_validos'].ge(30))
    return out

def grafico_escolaridade(tabela,caminho):
    dados=tabela.pivot_table(index='escolaridade',columns='tipo_mov',values='percentual_grupo_tipo_mov',aggfunc='sum',fill_value=0)
    ax=dados.plot.barh(figsize=(11,7)); ax.set_xlabel('% dentro do tipo de movimentação'); ax.set_ylabel('Escolaridade observada')
    ax.set_title('Escolaridade de admitidos e desligados')
    for container, tipo in zip(ax.containers,dados.columns):
        contagem=tabela[tabela['tipo_mov'].eq(tipo)].set_index('escolaridade')['quantidade'].reindex(dados.index,fill_value=0)
        ax.bar_label(container,labels=[f'{pct:.1f}% (n={int(n):,})' for pct,n in zip(dados[tipo],contagem)],fontsize=6,padding=2)
    ax.margins(x=.3)
    ax.figure.savefig(caminho,dpi=150,bbox_inches='tight'); plt.close(ax.figure)

def grafico_salario(tabela,caminho):
    dados=tabela.set_index('tipo_mov')
    fig,ax=plt.subplots(figsize=(8,5)); bars=ax.bar(dados.index,dados['salario_medio'],label='Média')
    ax.scatter(dados.index,dados['salario_mediano'],marker='D',color='black',label='Mediana')
    for barra,(_,row) in zip(bars,dados.iterrows()): ax.text(barra.get_x()+barra.get_width()/2,barra.get_height(),f"R$ {row['salario_medio']:.2f}\nn={int(row['salarios_validos']):,} ({row['pct_salarios_validos_movimentacoes_grupo']:.1f}%)",ha='center',fontsize=8)
    ax.set_title('Salário mensal nominal e cobertura'); ax.set_ylabel('R$'); ax.legend(); ax.margins(y=.25)
    fig.savefig(caminho,dpi=150,bbox_inches='tight'); plt.close(fig)

def grafico_setor_escolaridade(tabela,caminho):
    top=tabela.groupby('setor',dropna=False)['salarios_validos'].sum().nlargest(8).index
    dados=tabela[tabela['setor'].isin(top)].pivot_table(index='setor',columns='escolaridade',values='salario_mediano',aggfunc='mean')
    fig,ax=plt.subplots(figsize=(13,7)); img=ax.imshow(dados.fillna(0),aspect='auto',cmap='Blues')
    ax.set_yticks(range(len(dados.index)),dados.index.str.slice(0,48)); ax.set_xticks(range(len(dados.columns)),dados.columns,rotation=45,ha='right')
    ax.set_title('Mediana salarial por setor e escolaridade (R$; zero indica ausência)'); fig.colorbar(img,ax=ax,label='R$')
    for y,setor in enumerate(dados.index):
        for x,escolaridade in enumerate(dados.columns):
            item=tabela[(tabela['setor'].eq(setor)) & (tabela['escolaridade'].eq(escolaridade))]
            if not item.empty and item.iloc[0]['salarios_validos']:
                r=item.iloc[0]; pct=r['remuneracao_relativa_pct_referencia']
                texto=f"{int(r['salarios_validos'])}\n{pct:.0f}%" if pd.notna(pct) else f"{int(r['salarios_validos'])}\n—"
                ax.text(x,y,texto,ha='center',va='center',fontsize=5)
    ax.set_xlabel('Em cada célula: número de salários válidos / % da referência estadual')
    fig.savefig(caminho,dpi=150,bbox_inches='tight'); plt.close(fig)

def grafico_diferencas(tabela,caminho):
    dados=tabela[tabela['amostra_suficiente']].copy()
    dados=dados.reindex(dados['diferenca_media_reais'].abs().nlargest(10).index).sort_values('diferenca_media_reais')
    if dados.empty: return
    fig,ax=plt.subplots(figsize=(12,7)); barras=ax.barh(dados['setor'].str.slice(0,50),dados['diferenca_media_reais'])
    for barra,(_,linha) in zip(barras,dados.iterrows()):
        ax.annotate(f"{linha['diferenca_media_reais']:+.0f} R$ ({linha['diferenca_media_pct_desligados']:+.1f}%)",(barra.get_width(),barra.get_y()+barra.get_height()/2),fontsize=7)
    ax.axvline(0,color='black',linewidth=.5); ax.set_title('Diferença salarial: admitidos − desligados'); ax.set_xlabel('Reais e percentual da média dos desligados'); ax.margins(x=.45)
    fig.savefig(caminho,dpi=150,bbox_inches='tight'); plt.close(fig)

def analisar(df,saida):
    setor=['cnae_divisao','setor']; municipio=['codigo_ibge_7d','nome_municipio']
    geral=salarios(df,[]); esc=distribuicao(df,[],'escolaridade'); faixa=distribuicao(df,[],'faixa_salarial')
    setesc=salarios(df,setor+['codigo_escolaridade','escolaridade'])
    ranking=diferencas(df,setor).sort_values('diferenca_media_reais')
    adm=df[df['admissoes'].eq(1)]
    alto=adm.groupby(setor,dropna=False,observed=True).agg(admitidos=('admissoes','sum'),superior_completo=('superior_completo','sum'),salarios_validos=('salario_valido','count'),n_admitidos_com_referencia=('salario_relativo_referencia','count'),indice_relativo_mediano=('salario_relativo_referencia','median')).reset_index()
    alto['pct_superior_completo_admitidos_setor']=alto['superior_completo'].div(alto['admitidos'].where(alto['admitidos'].ne(0))).mul(100)
    alto['remuneracao_pct_referencia_estadual']=alto['indice_relativo_mediano']*100
    eleg=alto[alto['admitidos'].ge(30)&alto['n_admitidos_com_referencia'].ge(30)]
    q=eleg['pct_superior_completo_admitidos_setor'].quantile(.75)
    alto['escolaridade_alta_remuneracao_relativa_baixa']=alto['admitidos'].ge(30)&alto['n_admitidos_com_referencia'].ge(30)&alto['pct_superior_completo_admitidos_setor'].ge(q)&alto['indice_relativo_mediano'].lt(1)
    tabelas={'escolaridade_movimento':esc,'faixa_salarial_movimento':faixa,'salarios_movimento':geral,
      'salarios_setor_movimento':salarios(df,setor),'salarios_municipio_movimento':salarios(df,municipio),
      'salarios_escolaridade_movimento':salarios(df,['codigo_escolaridade','escolaridade']),
      'salarios_setor_escolaridade_movimento':setesc,
      'escolaridade_setor_movimento':distribuicao(df,setor,'escolaridade'),
      'diferencas_setor':ranking,'diferencas_escolaridade':diferencas(df,['codigo_escolaridade','escolaridade']),
      'setores_escolaridade_remuneracao':alto}
    pasta=saida/'eixo2_socioeconomico'; exportar(tabelas,pasta)
    grafico_escolaridade(esc,pasta/'escolaridade.png'); grafico_salario(geral,pasta/'salarios_admitidos_desligados.png')
    grafico_setor_escolaridade(agregar(df,setor+['codigo_escolaridade','escolaridade']),pasta/'setor_escolaridade_salario.png')
    grafico_diferencas(ranking,pasta/'ranking_diferencas_salariais.png')
    return tabelas

def main():
    args=argumentos(); df,_=dados_comuns(args); analisar(df,args.saida)
if __name__=='__main__': main()
