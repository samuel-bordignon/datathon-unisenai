"""Eixo 3: CBOs e macrofamílias ocupacionais."""
from comum import argumentos,dados_comuns,agregar,distribuicao,exportar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def analisar(df,saida):
    cbos=agregar(df,['cbo','descricao_cbo','macrofamilia','funcao_profissional'])
    familias=agregar(df,['macrofamilia'])
    educ=distribuicao(df,['macrofamilia'],'escolaridade')
    pred=educ.sort_values(['macrofamilia','tipo_mov','quantidade','escolaridade'],ascending=[True,True,False,True]).drop_duplicates(['macrofamilia','tipo_mov'])
    tabelas={'cbos':cbos.sort_values('movimentacoes',ascending=False),
      'macrofamilias':familias.sort_values('admissoes',ascending=False),
      'macrofamilias_ranking_saldo':familias.sort_values('saldo',ascending=False),
      'escolaridade_macrofamilia':educ,'escolaridade_predominante':pred,
      'salarios_macrofamilia_movimento':agregar(df,['macrofamilia','tipo_mov']),
      'macrofamilias_mensal':agregar(df,['competencia','macrofamilia']),
      'ocupacoes_mensal':agregar(df,['competencia','cbo','descricao_cbo','macrofamilia'])}
    pasta=saida/'eixo3_qualificacao'; exportar(tabelas,pasta)
    top=familias.nlargest(10,'admissoes').sort_values('admissoes')
    fig,ax=plt.subplots(figsize=(11,7)); bars=ax.barh(top['macrofamilia'],top['admissoes'])
    for bar,(_,r) in zip(bars,top.iterrows()):
        ax.annotate(f"{int(r['admissoes']):,} ({r['pct_admissoes_total_sc']:.1f}% SC)",(bar.get_width(),bar.get_y()+bar.get_height()/2),va='center',fontsize=8)
    ax.margins(x=.35); ax.set_xlabel('Admissões e percentual das admissões em SC'); ax.set_title('Macrofamílias com mais admissões')
    fig.savefig(pasta/'macrofamilias_admissoes.png',dpi=150,bbox_inches='tight'); plt.close(fig)
    return tabelas

def main():
    args=argumentos(); df,_=dados_comuns(args); analisar(df,args.saida)
if __name__=='__main__': main()
