"""Fumaça do painel: executa cada aba com o AppTest do Streamlit e falha se houver exceção.

Uso: python src/teste_dashboard_abas.py  (requer a base gerada por preparar_dashboard.py)
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

PAINEL = Path(__file__).resolve().parents[1] / 'dashboard.py'


def executar(aba, filtros=None):
    at = AppTest.from_file(str(PAINEL), default_timeout=300).run()
    for rotulo, valor in (filtros or {}).items():
        next(m for m in at.multiselect if m.label == rotulo).set_value(valor)
    at.run()
    navegacao = next(r for r in at.radio if r.label == 'Navegação')
    navegacao.set_value(aba).run()
    if at.exception:
        raise SystemExit(f'Falha em {aba} {filtros or ""}: {at.exception[0].message}')
    return at


def main():
    at = AppTest.from_file(str(PAINEL), default_timeout=300).run()
    abas = next(r for r in at.radio if r.label == 'Navegação').options
    for filtros in [None, {'Município': ['Concórdia']}]:
        for aba in abas:
            resultado = executar(aba, filtros)
            print(f'OK  {aba:<30} {filtros or "SC completo"}  gráficos={len(resultado.get("plotly_chart"))}')


if __name__ == '__main__':
    sys.exit(main())
