"""Materializa classificação assistida por IA, baseada em títulos oficiais.

As regras semânticas foram elaboradas pelo assistente nesta implementação;
a aplicação é determinística e as classificações não foram revisadas uma a uma.
"""
import unicodedata
import pandas as pd
from comum import ENTRADA, REFERENCIAS, CATALOGO, dicionario

# Taxonomia e precedências propostas pela IA; usa somente código e título.
REGRAS = [
 ('Tecnologia da informação e dados',r'programador|desenvolvedor|sistemas de inform|analista de (?:sistema|dados|tecnologia)|comput|informatica|software|redes de computador'),
 ('Engenharia, pesquisa e projetos',r'engenheir|arquiteto|pesquisador|cientista|estatistic|quimico|fisico|biologo|geologo|desenhista projetista'),
 ('Gestão e direção',r'^diretor|^gerente|^superintendente|^presidente|^administrador|^chefe|^supervisor|^coordenador'),
 ('Técnicos e controle de qualidade',r'^tecnico|^tecnologo|inspetor de qualidade|controle de qualidade|laboratorista'),
 ('Construção e infraestrutura',r'pedreiro|servente de obras|carpinteiro|armador de estrutura|pintor de obras|construcao civil|azulejista|encanador|gesseiro|mestre de obras|instalador hidraul|concreto|alvenaria'),
 ('Alimentos e bebidas',r'magarefe|acougueiro|padeiro|confeiteiro|abatedor|carnes|laticini|alimento|bebidas|frigorific|pescado'),
 ('Têxtil, vestuário e couro',r'costureir|confeccao|tecel|fiacao|fiador|tear|tecido|textil|vestuario|calcad|sapateiro|couro|bordador|alfaiate|modelista de roupas|malharia'),
 ('Madeira, móveis, papel e gráfica',r'marceneir|moveis|madeira|madeireir|serraria|carpinteiro de moveis|celulose|papel|grafico|impressor|encadernador'),
 ('Metalmecânica e metalurgia',r'soldador|metalurg|metalico|metais|metal|fundidor|torneiro mecanico|usinag|ferramenteir|caldeireiro|serralheiro|estampador de metal|chapas de metal'),
 ('Elétrica, eletrônica e automação',r'eletricista|eletricidade|eletroeletron|eletronica|eletronico|eletrotecn|eletric|automacao'),
 ('Manutenção e reparação',r'mecanico|manutencao|reparador|ajustador mecanico|lubrificador|consertador'),
 ('Química, plástico, borracha e minerais',r'plastico|borracha|quimic|petroquim|ceram|vidro|cimento|minerais|mineral|pintor industrial'),
 ('Logística, transporte e armazenagem',r'motorista|caminhao|condutor|transporte|almoxarif|expedidor|empilhadeira|estoquista|armazen|logistic|carga e descarga|conferente de carga'),
 ('Agropecuária e atividades florestais',r'agropecuar|agricult|florestal|pecuar|criador de|tratador de animais|trabalhador rural|jardineiro|jardinagem'),
 ('Extração, energia e saneamento',r'minerador|mineracao|extracao|saneamento|tratamento de agua|tratamento de esgoto|usina eletrica|geracao de energia'),
 ('Saúde, educação e serviços especializados',r'enfermeir|medico|dentista|farmaceutic|professor|pedagogo|psicolog|fisioterapeuta|nutricionista|advogad|assistente social'),
 ('Segurança, limpeza e serviços de apoio',r'faxineir|limpeza|vigilante|porteiro|seguranca|cozinheiro|copeiro|zelador|auxiliar de servicos gerais'),
 ('Administração, finanças e comércio',r'escritorio|administrativ|secretari|contabil|contad|financeir|comprador|vendedor|comercial|recepcionista|recursos humanos|departamento pessoal|caixa|atendente'),
 ('Produção e apoio industrial',r'alimentador de linha|auxiliar de producao|auxiliar de fabrica|embalador|operador de maquina|montador|operador de producao|ajudante de producao|producao industrial'),
]
FALLBACK = {'1':'Gestão e direção','2':'Engenharia, pesquisa e projetos','3':'Técnicos e controle de qualidade',
 '4':'Administração, finanças e comércio','5':'Segurança, limpeza e serviços de apoio',
 '6':'Agropecuária e atividades florestais','7':'Produção e apoio industrial',
 '8':'Produção e apoio industrial','9':'Manutenção e reparação'}

def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(texto).lower()) if not unicodedata.combining(c))

def main():
    base = pd.read_csv(ENTRADA,sep=';',usecols=['cbo2002ocupação'],dtype='string')
    codigos = base['cbo2002ocupação'].dropna().str.zfill(6).drop_duplicates().sort_values().rename('cbo').to_frame()
    local = dicionario('cbo2002ocupação').rename(columns={'codigo':'cbo','descricao':'descricao_cbo'})
    local['cbo'] = local['cbo'].str.zfill(6)
    oficial = pd.read_csv(REFERENCIAS/'cbo_ocupacoes.csv',sep=';',encoding='latin-1',dtype='string').rename(columns={'CODIGO':'cbo','TITULO':'descricao_mte'})
    oficial['cbo'] = oficial['cbo'].str.zfill(6)
    cat = codigos.merge(local,on='cbo',how='left',validate='one_to_one').merge(oficial[['cbo','descricao_mte']].drop_duplicates('cbo'),on='cbo',how='left',validate='one_to_one')
    cat['fonte_descricao'] = 'Dicionário CAGED'
    cat.loc[cat['descricao_cbo'].isna() & cat['descricao_mte'].notna(),'fonte_descricao'] = 'Catálogo MTE'
    cat.loc[cat['descricao_cbo'].isna() & cat['descricao_mte'].isna(),'fonte_descricao'] = 'Não encontrada'
    cat['descricao_cbo'] = cat['descricao_cbo'].fillna(cat['descricao_mte'])
    titulo = cat['descricao_cbo'].fillna('').map(normalizar)
    cat['macrofamilia'] = pd.Series(pd.NA,index=cat.index,dtype='string')
    cat['justificativa'] = pd.Series(pd.NA,index=cat.index,dtype='string')
    for familia,regex in REGRAS:
        mascara = cat['macrofamilia'].isna() & titulo.str.contains(regex,regex=True)
        cat.loc[mascara,'macrofamilia'] = familia
        cat.loc[mascara,'justificativa'] = 'Título ocupacional indica atuação em '+familia.lower()+'.'
    restante = cat['macrofamilia'].isna() & cat['descricao_cbo'].notna()
    cat.loc[restante,'macrofamilia'] = cat.loc[restante,'cbo'].str[0].map(FALLBACK).fillna('Outras ocupações')
    cat.loc[restante,'justificativa'] = 'Classificação ampla pelo grande grupo CBO; requer revisão do título.'
    pendente = cat['descricao_cbo'].isna()
    cat.loc[pendente,'macrofamilia'] = 'Pendente de classificação'
    cat.loc[pendente,'justificativa'] = 'Descrição oficial não encontrada; classificação pendente.'
    cat['funcao_profissional'] = cat['descricao_cbo'].fillna('Não identificada')
    cat['metodo'] = 'Regras semânticas elaboradas por IA; aplicação automática sem revisão individual'
    cat.drop(columns='descricao_mte').to_csv(CATALOGO,sep=';',index=False,encoding='utf-8-sig')
    print('CBOs:',len(cat),'pendentes:',int(pendente.sum()),'classificação ampla:',int(restante.sum()))

if __name__ == '__main__': main()
