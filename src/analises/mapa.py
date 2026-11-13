"""Adapta a orientação dos anéis GeoJSON à projeção geográfica do Plotly/D3."""
from copy import deepcopy


def orientar_malha(geojson):
    """Retorna uma cópia com exteriores horários e eventuais buracos anti-horários."""
    resultado = deepcopy(geojson)
    for feature in resultado.get('features', []):
        geometria = feature.get('geometry') or {}
        tipo = geometria.get('type')
        if tipo not in ('Polygon', 'MultiPolygon'):
            continue
        poligonos = [geometria['coordinates']] if tipo == 'Polygon' else geometria['coordinates']
        for poligono in poligonos:
            for indice, anel in enumerate(poligono):
                area_dupla = sum(a[0] * b[1] - b[0] * a[1]
                                 for a, b in zip(anel, anel[1:] + anel[:1]))
                if (indice == 0 and area_dupla > 0) or (indice > 0 and area_dupla < 0):
                    anel.reverse()
    return resultado
