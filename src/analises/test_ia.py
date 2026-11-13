import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia import gemini  # noqa: E402
from ia.contexto import montar_contexto, serializar  # noqa: E402
from test_cenarios import dados  # noqa: E402

CHAVE = 'chave-secreta-123'


class Resposta:
    def __init__(self, status, corpo):
        self.status_code, self._corpo = status, corpo

    def json(self):
        return self._corpo


class GeminiTest(unittest.TestCase):
    def test_chave_no_header_e_fora_da_url(self):
        corpo = {'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]}
        with mock.patch.object(gemini.requests, 'post', return_value=Resposta(200, corpo)) as post:
            self.assertEqual(gemini.gerar('oi', CHAVE, sistema='s', json_saida=True), 'ok')
        url = post.call_args.args[0]
        self.assertNotIn(CHAVE, url)
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], CHAVE)
        enviado = post.call_args.kwargs['json']
        self.assertEqual(enviado['generationConfig']['responseMimeType'], 'application/json')
        self.assertEqual(enviado['systemInstruction']['parts'][0]['text'], 's')

    def test_erro_nao_expoe_chave(self):
        corpo = {'error': {'message': f'API key {CHAVE} inválida'}}
        with mock.patch.object(gemini.requests, 'post', return_value=Resposta(400, corpo)):
            with self.assertRaises(gemini.ErroIA) as erro:
                gemini.gerar('oi', CHAVE)
        self.assertNotIn(CHAVE, str(erro.exception))

    def test_sem_chave(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            chave, modelo = gemini.configuracao({})
        self.assertIsNone(chave)
        self.assertEqual(modelo, gemini.MODELO_PADRAO)
        with self.assertRaises(gemini.ErroIA):
            gemini.gerar('oi', None)


class ContextoTest(unittest.TestCase):
    def test_contexto_agregado_e_compacto(self):
        df = dados()
        df['demissoes_empresa'] = df.desligamentos - df.desligamentos_a_pedido
        for coluna in ['terminos_contrato', 'outros_desligamentos']:
            df[coluna] = 0
        df['nivel_atuacao'] = 'Operacional de base'
        df['cbo'], df['descricao_cbo'] = '784205', 'Alimentador de linha'
        texto = serializar(montar_contexto(df, df, 'teste'))
        contexto = json.loads(texto)
        self.assertLess(len(texto), 20000)
        self.assertEqual(contexto['kpis']['admissoes'], int(df.admissoes.sum()))
        for coluna in ['salario_valido', 'salario_relativo_referencia', 'idade']:
            self.assertNotIn(f'"{coluna}"', texto)


if __name__ == '__main__':
    unittest.main()
