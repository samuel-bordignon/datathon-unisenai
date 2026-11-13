"""Contexto agregado enviado ao Gemini. Só tabelas resumidas; nenhum microdado sai da máquina."""
import json

import pandas as pd

from cenarios import agregar, cbos_deficit, desagio_escolaridade, divergente, municipios, sinais

SISTEMA = """Você é analista de dados de uma consultoria contratada pela FIESC para o Datathon "Raio-X do Mercado de Trabalho Industrial de SC".
Pergunta central: quais regiões e setores industriais de SC enfrentam apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?
Regras obrigatórias:
- Use somente os números do CONTEXTO (JSON). Não invente valores, municípios, setores nem fontes externas.
- Cite o número que sustenta cada afirmação, no formato brasileiro (1.234; 12,5%).
- Escreva como hipótese ("sugere", "é compatível com"), nunca como causa comprovada.
- O CAGED mede fluxos (admissões e desligamentos), não vagas abertas; escolaridade é a do trabalhador, não a exigida pelo cargo.
- Diferença salarial entre quem entra e quem sai é compatível com compressão salarial OU com maior tempo de casa de quem sai.
- Responda em português do Brasil, de forma objetiva."""

PROMPT_HIPOTESES = """Gere de 3 a 5 hipóteses e recomendações para o recorte do CONTEXTO.
Responda apenas JSON no formato:
{"hipoteses": [{"titulo": str, "evidencia": str, "macrofamilia": str, "recomendacao": str}], "limites": [str]}
"evidencia" deve citar números do contexto. "macrofamilia" deve ser uma macrofamília presente no contexto.
CONTEXTO:
"""


def _registros(tabela, colunas, casas=1):
    return [{k: (round(v, casas) if isinstance(v, float) else v) for k, v in linha.items()}
            for linha in tabela[[c for c in colunas if c in tabela.columns]].to_dict('records')]


def montar_contexto(estado, recorte, escopo):
    """Resumo do recorte em dicionário serializável (KPIs, rankings, polos, salários e motivos)."""
    total = agregar(recorte, []).iloc[0]
    mun = municipios(estado, recorte)
    setores = agregar(recorte, ['setor'])
    polos = sinais(estado, recorte)
    polos = polos[polos.sinal_retencao].sort_values('movimentacoes', ascending=False).head(10)
    _, desagio = desagio_escolaridade(recorte)
    niveis = agregar(recorte, ['nivel_atuacao'])
    familias = agregar(recorte, ['macrofamilia']).sort_values('movimentacoes', ascending=False).head(12)
    deficit = cbos_deficit(recorte, 8)
    motivos = ['pedidos', 'demissoes_empresa', 'terminos_contrato', 'outros_desligamentos']
    contexto = {
        'escopo': escopo,
        'periodo': [int(recorte.competencia.min()), int(recorte.competencia.max())],
        'kpis': {'admissoes': int(total.admissoes), 'desligamentos': int(total.desligamentos), 'saldo': int(total.saldo),
                 'pct_pedidos_demissao': round(float(total.pct_pedidos), 1),
                 'mediana_salario_admitidos': round(float(recorte[recorte.admissoes.eq(1)].salario_valido.median()), 0)},
        'municipios_maiores_e_menores_saldos': _registros(divergente(mun, 'saldo'), ['nome_municipio', 'saldo', 'saldo_10000', 'admissoes', 'desligamentos']),
        'setores_maiores_e_menores_saldos': _registros(divergente(setores, 'saldo'), ['setor', 'saldo', 'admissoes', 'desligamentos', 'pct_pedidos']),
        'polos_sinal_retencao': _registros(polos, ['nome_municipio', 'setor', 'macrofamilia_predominante', 'movimentacoes', 'saldo', 'pct_pedidos', 'remuneracao_relativa_pct']),
        'salario_mediano_por_escolaridade': _registros(desagio.assign(escolaridade=desagio.escolaridade.astype(str)),
            ['escolaridade', 'mediana_Admitidos', 'mediana_Pedido de demissão (40)', 'mediana_Demissão pela empresa (31)',
             'n_Admitidos', 'desagio_mediana_Demissão pela empresa (31)'], 0),
        'nivel_atuacao_motivos': _registros(niveis, ['nivel_atuacao', 'admissoes', 'desligamentos', 'saldo'] + motivos),
        'macrofamilias': _registros(familias, ['macrofamilia', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano']),
        'cbos_maior_deficit': _registros(deficit, ['descricao_cbo', 'nivel_atuacao', 'macrofamilia', 'deficit', 'motivo_dominante', 'pct_motivo_dominante']),
        'definicoes': {'saldo': 'admissões − desligamentos', 'pct_pedidos': 'desligamentos a pedido (código 40) / desligamentos',
                       'desagio': '(mediana admitidos − mediana grupo) / mediana grupo, %',
                       'remuneracao_relativa_pct': 'mediana dos admitidos sobre a mediana estadual da mesma escolaridade e mês, %',
                       'sinal_retencao': 'volume no quartil superior, % pedidos acima de SC e remuneração relativa < 100%'},
    }
    return contexto


def serializar(contexto):
    return json.dumps(contexto, ensure_ascii=False, separators=(',', ':'), default=lambda v: None if pd.isna(v) else str(v))
