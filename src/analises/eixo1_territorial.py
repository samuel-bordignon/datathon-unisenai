"""Eixo 1: análise territorial e setorial."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from matplotlib.colors import TwoSlopeNorm
from comum import argumentos, dados_comuns, agregar, exportar, REFERENCIAS

def mapa(tabela, caminho):
    geo = json.loads((REFERENCIAS/'malha_sc.geojson').read_text(encoding='utf-8'))
    valores = tabela.set_index('codigo_ibge_7d')['saldo'].to_dict()
    patches, cores = [], []
    for feature in geo['features']:
        cod = str(feature['properties']['codarea']).zfill(7)
        geometry = feature['geometry']; coords = geometry['coordinates']
        polys = [coords] if geometry['type']=='Polygon' else coords
        for pol in polys:
            patches.append(Polygon(pol[0],closed=True)); cores.append(valores.get(cod,0))
    limite = max(abs(min(cores)),abs(max(cores)),1)
    fig, ax = plt.subplots(figsize=(11,8))
    collection = PatchCollection(patches,cmap='RdBu',norm=TwoSlopeNorm(vmin=-limite,vcenter=0,vmax=limite),edgecolor='white',linewidth=0.15)
    collection.set_array(cores); ax.add_collection(collection); ax.autoscale_view(); ax.set_aspect('equal')
    ax.set_title('Saldo de empregos industriais por município'); ax.set_axis_off()
    fig.colorbar(collection,ax=ax,label='Saldo (admissões − desligamentos)',shrink=.7)
    fig.savefig(caminho,dpi=160,bbox_inches='tight'); plt.close(fig)

def barras(tabela, coluna, caminho, titulo, percentual):
    dados = tabela.nlargest(12,coluna).sort_values(coluna)
    fig,ax=plt.subplots(figsize=(12,7)); barras=ax.barh(dados['setor'].str.slice(0,55),dados[coluna])
    maior=max(dados[coluna].max(),1)
    for barra,(_,linha) in zip(barras,dados.iterrows()):
        ax.text(barra.get_width()+maior*.01,barra.get_y()+barra.get_height()/2,f"{int(linha[coluna]):,} ({linha[percentual]:.1f}% SC)",va='center',fontsize=8)
    ax.set_xlim(0,maior*1.35); ax.set_title(titulo); ax.set_xlabel('Movimentações e participação no total estadual')
    fig.savefig(caminho,dpi=150,bbox_inches='tight'); plt.close(fig)

def analisar(df, saida):
    municipio = agregar(df,['codigo_ibge_7d','nome_municipio','populacao_estimada_2026'])
    municipio['saldo_por_10000_habitantes'] = municipio['saldo'].div(municipio['populacao_estimada_2026'].where(municipio['populacao_estimada_2026'].gt(0))).mul(10000)
    q = municipio['saldo_por_10000_habitantes'].quantile(.75)
    municipio['crescimento_expressivo'] = municipio['saldo'].gt(0) & municipio['saldo_por_10000_habitantes'].ge(q)
    setor = agregar(df,['secao','cnae_divisao','setor'])
    tabelas = {'municipios':municipio,'ranking_municipios':municipio.sort_values('saldo',ascending=False),
        'regioes_imediatas':agregar(df,['codigo_regiao_imediata','regiao_imediata']),
        'secoes':agregar(df,['secao']),'setores_divisao':setor,
        'subclasses':agregar(df,['secao','cnae_divisao','cnae_subclasse','descricao_subclasse']),
        'municipio_setor':agregar(df,['codigo_ibge_7d','nome_municipio','cnae_divisao','setor']),
        'municipios_mensal':agregar(df,['competencia','codigo_ibge_7d','nome_municipio']),
        'regioes_mensal':agregar(df,['competencia','codigo_regiao_imediata','regiao_imediata']),
        'setores_mensal':agregar(df,['competencia','secao','cnae_divisao','setor'])}
    pasta = saida/'eixo1_territorial'; exportar(tabelas,pasta)
    mapa(municipio,pasta/'mapa_saldo.png')
    barras(setor,'admissoes',pasta/'setores_admissoes.png','Setores com mais admissões','pct_admissoes_total_sc')
    barras(setor,'desligamentos',pasta/'setores_desligamentos.png','Setores com mais desligamentos','pct_desligamentos_total_sc')
    return tabelas

def main():
    args=argumentos(); df,_=dados_comuns(args); analisar(df,args.saida)
if __name__=='__main__': main()
