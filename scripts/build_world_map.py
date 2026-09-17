"""Rebuild the bundled map from Natural Earth's public-domain 110m boundaries."""
import json
from pathlib import Path
from urllib.request import urlopen

SOURCE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson'


def build(features):
    paths = []
    for feature in features:
        props = feature['properties']
        if props['ADM0_A3'] == 'ATA':
            continue
        code = props['ISO_A3_EH']
        if code == '-99':
            code = props['ADM0_A3']
        if code == 'KOS':
            code = 'XKX'
        geometry = feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        segments = []
        for polygon in polygons:
            for ring in polygon:
                points = [f'{(lon + 180) * 2.5:.1f},{(85 - lat) * 2.5:.1f}' for lon, lat in ring]
                segments.append('M' + 'L'.join(points) + 'Z')
        paths.append({'code': code, 'name': props['NAME_LONG'], 'path': ''.join(segments)})
    return paths


if __name__ == '__main__':
    with urlopen(SOURCE, timeout=30) as response:
        data = json.load(response)
    target = Path(__file__).resolve().parents[1] / 'data' / 'world_map.json'
    target.write_text(json.dumps(build(data['features']), separators=(',', ':')) + '\n')
