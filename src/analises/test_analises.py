import unittest
import pandas as pd
from comum import agregar, distribuicao, elegibilidade_salarial
from eixo2_socioeconomico import diferencas

class AnalisesTest(unittest.TestCase):
    def setUp(self):
        self.df=pd.DataFrame({'competencia':[202509,202509,202509,202510], 'grupo':['A','A','B','B'],
            'saldo_mov':[1,-1,1,-1], 'admissoes':[1,0,1,0], 'desligamentos':[0,1,0,1],
            'desligamentos_a_pedido':[0,1,0,0], 'salario_valido':[1518.,2000.,None,2500.],
            'salario_relativo_referencia':[1.,None,None,None], 'tipo_mov':['Admissão','Desligamento','Admissão','Desligamento'],
            'escolaridade':['Pós-graduação','Médio','Pós-graduação','Médio']})

    def test_saldo_e_denominadores_mensais(self):
        out=agregar(self.df,['competencia','grupo']).set_index(['competencia','grupo'])
        self.assertEqual(out.loc[(202509,'A'),'saldo'],0)
        self.assertEqual(out.loc[(202509,'A'),'pct_admissoes_total_sc'],50)
        self.assertEqual(out.loc[(202509,'A'),'pct_desligamentos_total_sc'],100)
        self.assertTrue(pd.isna(out.loc[(202510,'B'),'pct_admissoes_total_sc']))
        self.assertEqual(out.loc[(202509,'A'),'pct_desligamentos_a_pedido_desligamentos_grupo'],100)

    def test_distribuicao_preserva_nulos_e_denominador(self):
        out=distribuicao(self.df,[],'escolaridade')
        self.assertEqual(out.groupby('tipo_mov')['quantidade'].sum().to_dict(),{'Admissão':2,'Desligamento':2})
        self.assertTrue(out.groupby('tipo_mov')['percentual_grupo_tipo_mov'].sum().eq(100).all())
        self.assertEqual(out[out['escolaridade'].eq('Pós-graduação')]['quantidade'].sum(),2)

    def test_limites_salariais_e_intermitencia(self):
        minimo=pd.Series([1000.]*7)
        salario=pd.Series([300.,150000.,299.,150001.,1000.,1000.,None])
        intermitente=pd.Series([0,0,0,0,1,9,0])
        faixa,valido=elegibilidade_salarial(salario,minimo,intermitente)
        self.assertEqual(faixa.tolist(),[True,True,False,False,True,True,False])
        self.assertEqual(valido.tolist(),[True,True,False,False,False,False,False])

    def test_grupo_sem_admitidos_ou_desligados(self):
        out=diferencas(self.df,['grupo']).set_index('grupo')
        self.assertEqual(out.loc['A','diferenca_media_reais'],-482)
        self.assertAlmostEqual(out.loc['A','diferenca_media_pct_desligados'],-24.1)
        self.assertTrue(pd.isna(out.loc['B','diferenca_media_reais']))
        self.assertFalse(bool(out.loc['A','amostra_suficiente']))

if __name__=='__main__': unittest.main()
