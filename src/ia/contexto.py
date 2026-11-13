"""Contexto agregado enviado ao Gemini. Só tabelas resumidas; nenhum microdado sai da máquina."""
import json
import re
import unicodedata

import pandas as pd

from cenarios import agregar, cbos_deficit, desagio_escolaridade, divergente, evolucao, municipios, sinais

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


APELIDOS_MUNICIPIO = {'floripa': 'Florianópolis', 'balneario': 'Balneário Camboriú', 'bc': 'Balneário Camboriú',
                      'jaragua': 'Jaraguá do Sul', 'sao bento': 'São Bento do Sul', 'sao miguel': 'São Miguel do Oeste'}
IGNORAR_TERMOS = {'como', 'qual', 'quais', 'onde', 'porque', 'para', 'sobre', 'esta', 'estao', 'tem', 'mais', 'menos',
                  'maior', 'menor', 'maiores', 'menores', 'saldo', 'saldos', 'setor', 'setores', 'municipio', 'municipios',
                  'cidade', 'cidades', 'regiao', 'estado', 'santa', 'catarina', 'industria', 'industrial', 'mercado',
                  'trabalho', 'vagas', 'dados', 'caged', 'admissoes', 'desligamentos', 'demissoes', 'pedidos', 'salario',
                  'salarios', 'renda', 'escolaridade', 'situacao', 'cenarios', 'explica', 'explicam', 'fale', ' diga'}


def _norm(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texto or '')) if not unicodedata.combining(c)).lower()


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
        'evolucao_mensal': _registros(evolucao(recorte), ['competencia', 'admissoes', 'desligamentos', 'saldo', 'saldo_acumulado']),
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
    if 'faixa_etaria' in recorte.columns:
        idades = agregar(recorte, ['faixa_etaria']).assign(faixa_etaria=lambda t: t.faixa_etaria.astype(str))
        contexto['faixa_etaria_motivos'] = _registros(idades, ['faixa_etaria', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos'] + motivos)
    return contexto


def detalhar_pergunta(estado, recorte, pergunta, historico=None):
    """Extrai dados específicos de municípios, regiões, setores ou ocupações citados na pergunta do chat."""
    textos = [*(h.get('texto', '') for h in (historico or []) if h.get('papel') == 'user'), pergunta or '']
    busca = _norm(' '.join(textos))
    busca_atual = _norm(pergunta)
    if not busca.strip():
        return {}
    detalhes = {}
    nomes_mun = sorted(estado.nome_municipio.dropna().astype(str).unique(), key=len, reverse=True)
    citados_mun = []
    for apelido, oficial in APELIDOS_MUNICIPIO.items():
        if re.search(rf'(?<!\w){re.escape(apelido)}(?!\w)', busca) and oficial in nomes_mun:
            citados_mun.append(oficial)
    for nome in nomes_mun:
        termo = _norm(nome)
        if len(termo) >= 3 and re.search(rf'(?<!\w){re.escape(termo)}(?!\w)', busca) and nome not in citados_mun:
            citados_mun.append(nome)
    if citados_mun:
        lista_mun = []
        for nome in citados_mun[:4]:
            sub = recorte[recorte.nome_municipio.eq(nome)]
            origem = 'recorte atual' if not sub.empty else 'estado (fora do filtro atual)'
            if sub.empty:
                sub = estado[estado.nome_municipio.eq(nome)]
            if sub.empty:
                continue
            m = municipios(estado, sub)
            setores_m = agregar(sub, ['setor']).sort_values('movimentacoes', ascending=False)
            polos_m = sinais(estado, sub).sort_values('movimentacoes', ascending=False)
            familias_m = agregar(sub, ['macrofamilia']).sort_values('movimentacoes', ascending=False)
            esc_m = agregar(sub, ['escolaridade']).assign(escolaridade=lambda t: t.escolaridade.astype(str))
            lista_mun.append({
                'nome_municipio': nome,
                'origem_dados': origem,
                'resumo': _registros(m, ['nome_municipio', 'populacao_estimada_2026', 'admissoes', 'desligamentos',
                                         'saldo', 'saldo_10000', 'pct_pedidos', 'salario_mediano', 'remuneracao_relativa_pct'])[0],
                'setores_mais_movimentados': _registros(setores_m.head(6), ['setor', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano']),
                'setores_maiores_e_menores_saldos': _registros(divergente(setores_m, 'saldo', 3), ['setor', 'saldo', 'admissoes', 'desligamentos', 'pct_pedidos']),
                'macrofamilias': _registros(familias_m.head(6), ['macrofamilia', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano']),
                'escolaridade': _registros(esc_m, ['escolaridade', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano']),
                'cbos_maior_deficit': _registros(cbos_deficit(sub, 5), ['descricao_cbo', 'macrofamilia', 'admissoes', 'desligamentos', 'deficit', 'motivo_dominante', 'pct_motivo_dominante']),
                'pares_setor_sinal_retencao': _registros(polos_m.head(5), ['setor', 'sinal_retencao', 'movimentacoes', 'saldo', 'pct_pedidos', 'remuneracao_relativa_pct']),
            })
        if lista_mun:
            detalhes['municipios_citados'] = lista_mun
    if 'regiao_imediata' in estado.columns:
        regioes = [r for r in estado.regiao_imediata.dropna().astype(str).unique()
                   if len(_norm(r)) >= 4 and re.search(rf'(?<!\w){re.escape(_norm(r))}(?!\w)', busca)]
        if regioes:
            sub_r = recorte[recorte.regiao_imediata.isin(regioes[:3])]
            if sub_r.empty:
                sub_r = estado[estado.regiao_imediata.isin(regioes[:3])]
            detalhes['regioes_imediatas_citadas'] = _registros(
                agregar(sub_r, ['regiao_imediata']), ['regiao_imediata', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano'])
    tokens = [t for t in re.findall(r'[a-z]{4,}', busca_atual or busca) if t not in IGNORAR_TERMOS]
    radicais = {t[:5] for t in tokens if len(t) >= 5} | set(tokens)
    if radicais:
        base_busca = recorte if not recorte.empty else estado
        setores_todos = agregar(base_busca, ['setor'])
        setores_match = setores_todos[setores_todos.setor.astype(str).map(
            lambda s: any(r in _norm(s) for r in radicais))].sort_values('movimentacoes', ascending=False).head(4)
        if not setores_match.empty:
            detalhes['setores_citados'] = []
            for linha in _registros(setores_match, ['setor', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano']):
                sub_s = base_busca[base_busca.setor.eq(linha['setor'])]
                mun_s = agregar(sub_s, ['nome_municipio'])
                linha['municipios_destaque'] = _registros(divergente(mun_s, 'saldo', 3), ['nome_municipio', 'saldo', 'admissoes', 'desligamentos', 'pct_pedidos'])
                detalhes['setores_citados'].append(linha)
        if 'descricao_cbo' in base_busca.columns:
            cbos_todos = agregar(base_busca, ['cbo', 'descricao_cbo', 'macrofamilia'])
            cbos_match = cbos_todos[cbos_todos.descricao_cbo.astype(str).map(
                lambda s: any(r in _norm(s) for r in radicais))].sort_values('movimentacoes', ascending=False).head(6)
            if not cbos_match.empty:
                detalhes['cbos_citadas'] = _registros(cbos_match, ['descricao_cbo', 'macrofamilia', 'admissoes', 'desligamentos', 'saldo', 'pct_pedidos', 'salario_mediano'])
    return detalhes


def serializar(contexto):
    return json.dumps(contexto, ensure_ascii=False, separators=(',', ':'), default=lambda v: None if pd.isna(v) else str(v))
