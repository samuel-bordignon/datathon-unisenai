"""Materializa os dados enriquecidos para consultas interativas, sem alterar os eixos."""
import json
import shutil
from datetime import datetime, timezone

from comum import argumentos, carregar, REFERENCIAS

COLUNAS = ['competencia', 'codigo_ibge_7d', 'nome_municipio',
           'populacao_estimada_2026', 'codigo_regiao_imediata', 'regiao_imediata',
           'cnae_divisao', 'setor', 'cbo', 'descricao_cbo', 'macrofamilia',
           'funcao_profissional', 'codigo_escolaridade', 'escolaridade', 'tipo_mov',
           'admissoes', 'desligamentos', 'desligamentos_a_pedido', 'salario_valido',
           'salario_relativo_referencia', 'faixa_salarial']


def main():
    args = argumentos()
    df, auditoria = carregar(args)
    destino = args.saida / 'dashboard'
    destino.mkdir(parents=True, exist_ok=True)
    df[COLUNAS].to_parquet(destino / 'movimentacoes.parquet', index=False)
    if (REFERENCIAS / 'malha_sc.geojson').exists():
        shutil.copyfile(REFERENCIAS / 'malha_sc.geojson', destino / 'malha_sc.geojson')
    metadados = {'gerado_em_utc': datetime.now(timezone.utc).isoformat(),
                 'entrada': str(args.entrada), 'auditoria': auditoria,
                 'periodo_observado': [int(df.competencia.min()), int(df.competencia.max())],
                 'linhas': len(df)}
    (destino / 'metadados.json').write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(df):,} movimentações preparadas em {destino}')


if __name__ == '__main__':
    main()
