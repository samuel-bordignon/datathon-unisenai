import unittest
import numpy as np
import pandas as pd
from cenarios import (agregar, dividir, distribuicao, evolucao, municipios, sinais, desagio_escolaridade,
                      divergente, cbos_deficit, motivos)


def salarios():
    linhas = []
    for esc, adm, ped, emp, n in [('Médio Completo', 2000, 2100, 2500, 40), ('Doutorado', 5000, 5200, 8000, 5)]:
        for grupo, valor in [('adm', adm), ('ped', ped), ('emp', emp)]:
            for _ in range(n):
                linhas.append(dict(escolaridade=esc, salario_valido=float(valor), admissoes=int(grupo == 'adm'),
                                   desligamentos=int(grupo != 'adm'), desligamentos_a_pedido=int(grupo == 'ped'),
                                   demissoes_empresa=int(grupo == 'emp')))
    return pd.DataFrame(linhas)


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

    def test_desagio_e_amostra_minima(self):
        _, largo = desagio_escolaridade(salarios())
        medio = largo.set_index('escolaridade').loc['Médio Completo']
        self.assertAlmostEqual(medio['desagio_mediana_Demissão pela empresa (31)'], -20.0)
        self.assertAlmostEqual(medio['desagio_mediana_Pedido de demissão (40)'], 100 * (2000 - 2100) / 2100)
        self.assertTrue(medio['suficiente_Demissão pela empresa (31)'])
        self.assertFalse(largo.set_index('escolaridade').loc['Doutorado', 'suficiente_Demissão pela empresa (31)'])

    def test_divergente_sem_repeticao(self):
        tabela = pd.DataFrame({'nome': list('abcd'), 'saldo': [10, 3, -2, -8]})
        out = divergente(tabela, 'saldo', n=5)
        self.assertEqual(out.nome.tolist(), ['d', 'c', 'b', 'a'])
        self.assertEqual(out.sentido.tolist(), ['Menores saldos'] * 2 + ['Maiores saldos'] * 2)

    def test_motivos_e_deficit(self):
        df = pd.DataFrame({'cbo': ['1', '1', '1', '2'], 'descricao_cbo': ['A', 'A', 'A', 'B'],
            'nivel_atuacao': ['Base'] * 4, 'admissoes': [1, 0, 0, 1], 'desligamentos': [0, 1, 1, 0],
            'desligamentos_a_pedido': [0, 1, 1, 0], 'demissoes_empresa': [0, 0, 0, 0],
            'terminos_contrato': [0, 0, 0, 0], 'outros_desligamentos': [0, 0, 0, 0],
            'salario_valido': [1.0] * 4, 'salario_relativo_referencia': [np.nan] * 4,
            'motivo_movimentacao': ['Admissão', 'Pedido de demissão (40)', 'Pedido de demissão (40)', 'Admissão']})
        out = cbos_deficit(df)
        self.assertEqual(out.cbo.tolist(), ['1'])
        self.assertEqual(out.iloc[0].motivo_dominante, 'Pedido de demissão (40)')
        m = motivos(df, 'cbo').set_index(['cbo', 'motivo_movimentacao'])
        self.assertEqual(m.loc[('1', 'Pedido de demissão (40)'), 'pct_fluxo'], 100)

    def test_denominadores_e_evolucao(self):
        df = dados()
        out = municipios(df, df).set_index('nome_municipio')
        self.assertTrue(pd.isna(out.loc['B', 'saldo_10000']))
        self.assertTrue(out.pct_saldo_sc.isna().all())
        self.assertTrue(pd.isna(dividir(1, 0)))
        self.assertTrue(pd.isna(evolucao(df).iloc[0].variacao_saldo_pct))


if __name__ == '__main__':
    unittest.main()
