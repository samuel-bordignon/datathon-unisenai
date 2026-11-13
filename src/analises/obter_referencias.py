"""Baixa referências públicas e mantém cópias locais para execução offline."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin
from datetime import datetime, timezone
import json
import requests

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / 'database' / 'doc' / 'referencias_analises'
FONTES = {
    'municipios.json': 'https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios',
    'cnae_divisoes.json': 'https://servicodados.ibge.gov.br/api/v2/cnae/divisoes',
    'malha_sc.geojson': 'https://servicodados.ibge.gov.br/api/v4/malhas/estados/42?formato=application%2Fvnd.geo%2Bjson&intrarregiao=municipio&qualidade=minima',
}
PAGINA_CBO = 'https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/cbo/servicos/downloads/downloads'

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.href = None; self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.href = dict(attrs).get('href')
    def handle_data(self, data):
        if self.href and 'CBO2002 - Ocupação' in data: self.links.append(self.href)
    def handle_endtag(self, tag):
        if tag == 'a': self.href = None

def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    page = requests.get(PAGINA_CBO, timeout=60); page.raise_for_status()
    parser = Links(); parser.feed(page.text)
    if not parser.links: raise RuntimeError('Link oficial de ocupações CBO não encontrado')
    fontes = {**FONTES, 'cbo_ocupacoes.csv': urljoin(PAGINA_CBO, parser.links[0])}
    metadata = {}
    for nome, url in fontes.items():
        response = requests.get(url, timeout=120); response.raise_for_status()
        (DESTINO / nome).write_bytes(response.content)
        metadata[nome] = {'url': response.url, 'obtido_em_utc': datetime.now(timezone.utc).isoformat(), 'bytes': len(response.content)}
        print(nome, len(response.content))
    (DESTINO / 'fontes.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__': main()
