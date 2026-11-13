"""Valida o catálogo de macrofamílias (regras semânticas) com uma classificação independente do Gemini.

O catálogo `catalogo_cbos_ia.csv` continua sendo a base reprodutível das análises; este script não o altera.
Ele envia lotes de CBOs (código e título) ao Gemini, compara as respostas com as regras e registra
a concordância simples e ponderada pelas movimentações. Execução retomável: cada lote respondido fica
salvo em `database/resultados/ia/lotes/`.

Uso (PowerShell):
    $env:GEMINI_API_KEY = "sua-chave"
    python src/analises/validar_catalogo_llm.py [--lote 100] [--pausa 4] [--limite N]
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from comum import CATALOGO, ENTRADA, SAIDA

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ia import gemini  # noqa: E402

PROMPT = Path(__file__).resolve().parents[1] / 'ia' / 'prompts' / 'classificar_cbo.txt'
PASTA = SAIDA / 'ia'
INVALIDA = 'Resposta inválida ou ausente'


def lotes(tabela, tamanho):
    return [tabela.iloc[i:i + tamanho] for i in range(0, len(tabela), tamanho)]


def montar_prompt(lote, familias):
    linhas = '\n'.join(f'{r.cbo}; {r.descricao_cbo}' for r in lote.itertuples())
    return PROMPT.read_text(encoding='utf-8').format(macrofamilias='\n'.join(f'- {f}' for f in familias), cbos=linhas)


def interpretar(texto, validas):
    """Converte a resposta JSON em {cbo: macrofamília}; nomes fora da lista viram resposta inválida."""
    limpo = texto.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    dados = json.loads(limpo)
    if isinstance(dados, dict):
        dados = next((v for v in dados.values() if isinstance(v, list)), [])
    saida = {}
    for item in dados:
        cbo = str(item.get('cbo', '')).strip().zfill(6)
        familia = str(item.get('macrofamilia', '')).strip()
        saida[cbo] = familia if familia in validas else INVALIDA
    return saida


def resumir(tabela):
    """Concordância simples (CBOs) e ponderada (movimentações)."""
    peso = tabela.movimentacoes.sum()
    return {'n_cbos': int(len(tabela)),
            'concordancia_pct': round(100 * tabela.concorda.mean(), 1) if len(tabela) else None,
            'concordancia_ponderada_pct': round(100 * tabela.movimentacoes[tabela.concorda].sum() / peso, 1) if peso else None,
            'respostas_invalidas': int(tabela.macrofamilia_llm.eq(INVALIDA).sum())}


def classificar_lote(prompt, chave, modelo, pausa, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            return gemini.gerar(prompt, chave, modelo, json_saida=True, timeout=180)
        except gemini.ErroIA as erro:
            if tentativa == tentativas or not any(c in str(erro) for c in ('429', '500', '503', 'conexão')):
                raise
            print(f'  {erro} — nova tentativa em {pausa * tentativa * 5:.0f} s')
            time.sleep(pausa * tentativa * 5)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--lote', type=int, default=100)
    parser.add_argument('--pausa', type=float, default=4.0, help='segundos entre lotes (cota gratuita)')
    parser.add_argument('--limite', type=int, help='validar só as N CBOs com mais movimentações')
    args = parser.parse_args()
    chave, modelo = gemini.configuracao()
    if not chave:
        raise SystemExit('Defina GEMINI_API_KEY antes de executar (veja o README).')
    catalogo = pd.read_csv(CATALOGO, sep=';', dtype={'cbo': 'string'}, encoding='utf-8-sig')
    pesos = pd.read_csv(ENTRADA, sep=';', usecols=['cbo2002ocupação'], dtype='string')['cbo2002ocupação'].str.zfill(6).value_counts()
    catalogo['movimentacoes'] = catalogo.cbo.map(pesos).fillna(0).astype(int)
    alvo = catalogo[catalogo.macrofamilia.ne('Pendente de classificação')].sort_values('movimentacoes', ascending=False)
    if args.limite:
        alvo = alvo.head(args.limite)
    familias = sorted(catalogo.macrofamilia[catalogo.macrofamilia.ne('Pendente de classificação')].unique())
    (PASTA / 'lotes').mkdir(parents=True, exist_ok=True)
    respostas = {}
    grupos = lotes(alvo.sort_values('cbo'), args.lote)
    for i, lote in enumerate(grupos, 1):
        arquivo = PASTA / 'lotes' / f'{modelo}_{args.lote}_{lote.cbo.iloc[0]}.json'
        if arquivo.exists():
            respostas.update(json.loads(arquivo.read_text(encoding='utf-8')))
            continue
        print(f'Lote {i}/{len(grupos)} ({len(lote)} CBOs)')
        try:
            texto = classificar_lote(montar_prompt(lote, familias), chave, modelo, args.pausa)
        except gemini.ErroIA as erro:
            raise SystemExit(f'{erro}\nLotes já respondidos ficam salvos; execute de novo para continuar.') from None
        try:
            parcial = interpretar(texto, set(familias))
        except (json.JSONDecodeError, AttributeError):
            print('  resposta fora do formato JSON; lote marcado como inválido')
            parcial = {}
        parcial = {c: parcial.get(c, INVALIDA) for c in lote.cbo}
        arquivo.write_text(json.dumps(parcial, ensure_ascii=False), encoding='utf-8')
        respostas.update(parcial)
        time.sleep(args.pausa)
    tabela = alvo[['cbo', 'descricao_cbo', 'macrofamilia', 'movimentacoes']].rename(columns={'macrofamilia': 'macrofamilia_regras'})
    tabela['macrofamilia_llm'] = tabela.cbo.map(respostas).fillna(INVALIDA)
    tabela['concorda'] = tabela.macrofamilia_regras.eq(tabela.macrofamilia_llm)
    tabela.to_csv(PASTA / 'validacao_catalogo.csv', sep=';', index=False, encoding='utf-8-sig')
    matriz = tabela[~tabela.concorda].groupby(['macrofamilia_regras', 'macrofamilia_llm']).agg(
        cbos=('cbo', 'size'), movimentacoes=('movimentacoes', 'sum')).reset_index().sort_values('movimentacoes', ascending=False)
    matriz.to_csv(PASTA / 'divergencias_catalogo.csv', sep=';', index=False, encoding='utf-8-sig')
    resumo = {'modelo': modelo, 'gerado_em_utc': datetime.now(timezone.utc).isoformat(), 'prompt': str(PROMPT.name), **resumir(tabela)}
    (PASTA / 'validacao_resumo.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Concordância {resumo['concordancia_pct']}% das CBOs ({resumo['concordancia_ponderada_pct']}% ponderada por movimentações); "
          f"{resumo['respostas_invalidas']} respostas inválidas. Arquivos em {PASTA}")


if __name__ == '__main__':
    main()
