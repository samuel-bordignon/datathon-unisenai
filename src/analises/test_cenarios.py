import unittest
import numpy as np
import pandas as pd
from cenarios import agregar, dividir, distribuicao, evolucao, municipios, sinais


def dados():
    linhas = []
    for cidade, n, pedido, relativo, saldo in [('A', 80, True, .8, 0), ('B', 40, False, 1.1, 0)]:
        for i in range(n):
            adm = i < n // 2 + saldo
            linhas.append(dict(competencia=202509, codigo_ibge_7d=cidade, nome_municipio=cidade,
                populacao_estimada_2026=1000 if cidade == 'A' else 0, codigo_regiao_imediata='1',
                regiao_imediata='R', cnae_divisao='10', setor='Alimentos', macrofamilia='Operação',
                admissoes=int(adm), desligamentos=int(not adm), desligamentos_a_pedido=int(not adm and pedido),
                salario_valido=float(i + 1000), salario_relativo_referencia=relativo if adm else np.nan,
                tipo_mov='Admissão' if adm else 'Desligamento', escolaridade='Médio'))
    return pd.DataFrame(linhas)


class CenariosTest(unittest.TestCase):
    def test_sinal_combina_criterios(self):
        df = dados()
        out = sinais(df, df).set_index('nome_municipio')
        self.assertTrue(out.loc['A', 'sinal_retencao'])
        self.assertFalse(out.loc['B', 'sinal_retencao'])
        df.loc[df.nome_municipio.eq('A'), 'salario_relativo_referencia'] = 1.2
        self.assertFalse(sinais(df, df).sinal_retencao.any())

    def test_setor_unico_por_municipio_item01(self):
        df = dados()
        df.loc[df.index % 3 == 0, 'macrofamilia'] = 'Produção e apoio industrial'
        out = sinais(df, df)
        self.assertFalse(out.duplicated(['codigo_ibge_7d', 'cnae_divisao']).any())
        a = out.set_index('nome_municipio').loc['A']
        self.assertEqual(a.macrofamilia_predominante, 'Operação')
        self.assertAlmostEqual(a.pct_macrofamilia_predominante, 100 * 53 / 80)

    def test_amostra_insuficiente_e_base_estadual(self):
        df = dados()
        selecionado = df[df.nome_municipio.eq('A')].head(35)
        out = sinais(df, selecionado).iloc[0]
        self.assertFalse(out.sinal_retencao)
        self.assertAlmostEqual(out.pct_pedidos_sc, 100 * 40 / 60)

    def test_mediana_verdadeira_e_distribuicao(self):
        df = dados()
        out = agregar(df, []).iloc[0]
        self.assertEqual(out.salario_mediano, df.salario_valido.median())
        self.assertEqual(distribuicao(df, 'escolaridade').quantidade.sum(), len(df))
        self.assertTrue(distribuicao(df, 'escolaridade').percentual.eq(100).all())

    def test_denominadores_e_evolucao(self):
        df = dados()
        out = municipios(df, df).set_index('nome_municipio')
        self.assertTrue(pd.isna(out.loc['B', 'saldo_10000']))
        self.assertTrue(out.pct_saldo_sc.isna().all())
        self.assertTrue(pd.isna(dividir(1, 0)))
        self.assertTrue(pd.isna(evolucao(df).iloc[0].variacao_saldo_pct))


if __name__ == '__main__':
    unittest.main()
