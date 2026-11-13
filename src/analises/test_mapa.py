import unittest
from mapa import orientar_malha


def area(anel):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(anel, anel[1:] + anel[:1]))


class MapaTest(unittest.TestCase):
    def test_orientacao_poligonos_e_buracos_sem_alterar_original(self):
        exterior = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
        buraco = [[1, 1], [1, 2], [2, 2], [2, 1], [1, 1]]
        original = {'features': [{'geometry': {'type': 'Polygon', 'coordinates': [exterior, buraco]}},
                                 {'geometry': {'type': 'MultiPolygon', 'coordinates': [[exterior]]}}]}
        corrigido = orientar_malha(original)
        self.assertGreater(area(original['features'][0]['geometry']['coordinates'][0]), 0)
        aneis = corrigido['features'][0]['geometry']['coordinates']
        self.assertLess(area(aneis[0]), 0)
        self.assertGreater(area(aneis[1]), 0)
        self.assertLess(area(corrigido['features'][1]['geometry']['coordinates'][0][0]), 0)
        self.assertEqual(orientar_malha(corrigido), corrigido)


if __name__ == '__main__':
    unittest.main()
