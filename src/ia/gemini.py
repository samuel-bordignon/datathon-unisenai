"""Cliente mínimo da API Gemini (REST generateContent) sem expor a chave.

Onde fica a chave:
  1. Dashboard: `.streamlit/secrets.toml` com `GEMINI_API_KEY = "..."` (arquivo ignorado pelo Git).
  2. Scripts ou alternativa: variável de ambiente `GEMINI_API_KEY`.
  Modelo opcional em `GEMINI_MODEL` (mesmos dois lugares).
A chave vai apenas no header `x-goog-api-key`; nunca na URL, em logs ou mensagens de erro.
"""
import os

import requests

URL = 'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent'
MODELO_PADRAO = 'gemini-3.5-flash-lite'


class ErroIA(RuntimeError):
    """Falha na chamada ao Gemini, com mensagem segura para exibir."""


def _ler(nome, segredos=None):
    if segredos is not None:
        try:
            valor = segredos.get(nome)
        except Exception:  # st.secrets lança erro se o arquivo não existir
            valor = None
        if valor:
            return str(valor)
    return os.environ.get(nome) or None


def configuracao(segredos=None):
    """Retorna (chave, modelo). A chave é None quando não configurada."""
    return _ler('GEMINI_API_KEY', segredos), _ler('GEMINI_MODEL', segredos) or MODELO_PADRAO


def _sanitizar(texto, chave):
    return texto.replace(chave, '***') if chave else texto


def gerar(prompt, chave, modelo=MODELO_PADRAO, sistema=None, historico=None, json_saida=False, timeout=90, sessao=None):
    """Envia o prompt e devolve o texto da resposta.

    historico: lista de dicts {'papel': 'user'|'model', 'texto': str} anteriores ao prompt.
    """
    if not chave:
        raise ErroIA('Chave do Gemini não configurada (GEMINI_API_KEY).')
    conteudos = [{'role': h['papel'], 'parts': [{'text': h['texto']}]} for h in (historico or [])]
    conteudos.append({'role': 'user', 'parts': [{'text': prompt}]})
    corpo = {'contents': conteudos}
    if sistema:
        corpo['systemInstruction'] = {'parts': [{'text': sistema}]}
    if json_saida:
        corpo['generationConfig'] = {'responseMimeType': 'application/json'}
    cliente = sessao or requests
    try:
        resposta = cliente.post(URL.format(modelo=modelo), json=corpo, timeout=timeout,
                                headers={'x-goog-api-key': chave, 'Content-Type': 'application/json'})
    except requests.RequestException as erro:
        raise ErroIA(_sanitizar(f'Falha de conexão com o Gemini: {type(erro).__name__}', chave)) from None
    if resposta.status_code != 200:
        try:
            detalhe = resposta.json().get('error', {}).get('message', '')
        except ValueError:
            detalhe = ''
        raise ErroIA(_sanitizar(f'Gemini respondeu {resposta.status_code}: {detalhe[:300]}', chave))
    dados = resposta.json()
    candidatos = dados.get('candidates') or []
    if not candidatos:
        motivo = dados.get('promptFeedback', {}).get('blockReason', 'sem candidatos')
        raise ErroIA(f'Gemini não retornou resposta ({motivo}).')
    partes = candidatos[0].get('content', {}).get('parts', [])
    texto = ''.join(p.get('text', '') for p in partes if not p.get('thought'))
    if not texto.strip():
        raise ErroIA('Gemini retornou resposta vazia.')
    return texto
