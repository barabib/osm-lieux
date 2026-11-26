#!/usr/bin/env python3
"""Lieux OpenStreetMap avec site ou e-mail, rangés par département.

Entrée : un fichier .osm.pbf déjà réduit par `osmium tags-filter` (lieux des
cibles + limites admin_level 6, objets référencés compris).
Sortie : un fichier <dep>.tsv par département de métropole (01 à 95, Corse
exclue), au format exact de la sortie CSV d'Overpass utilisée par le module
derf_prospect (tabulations, ligne d'en-tête), plus manifest.json.

Usage : extraire.py <lieux.pbf> <dossier_sortie> [horodatage_extrait]
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import osmium
import shapely
from shapely import wkb
from shapely.strtree import STRtree

# Mêmes cibles que DerfProspectWeb::query() (module 1.3.3).
KINDS = {
    'amenity': {'restaurant', 'bar', 'cafe', 'pub', 'fast_food', 'biergarten', 'nightclub',
                'food_court', 'events_venue', 'canteen'},
    'tourism': {'hotel', 'motel', 'guest_house', 'hostel', 'chalet', 'camp_site', 'caravan_site',
                'apartment', 'alpine_hut', 'wine_cellar'},
    'shop': {'wine', 'alcohol', 'beverages', 'deli', 'convenience', 'farm', 'cheese', 'general',
             'greengrocer', 'food', 'zero_waste', 'bulk'},
    'craft': {'caterer', 'winery', 'brewery', 'distillery'},
}
CONTACT = ('website', 'contact:website', 'url', 'email', 'contact:email')
COLUMNS = ['@type', '@id', '@lat', '@lon', 'name', 'addr:postcode', 'addr:city', 'website',
           'contact:website', 'url', 'email', 'contact:email', 'ref:FR:SIRET']
TAG_COLUMNS = COLUMNS[4:]
DEPS = ['%02d' % i for i in range(1, 96) if i != 20]
if os.environ.get('OSM_LIEUX_DEPS'):  # banc uniquement
    DEPS = os.environ['OSM_LIEUX_DEPS'].split(',')
DEP_RE = re.compile(r'^(\d{2})[A-Z]?$')
ISO_RE = re.compile(r'^FR-(\d{2})[A-Z]?$')


def is_target(tags):
    for k, values in KINDS.items():
        if tags.get(k) in values:
            return True
    return False


def has_contact(tags):
    return any(tags.get(k, '') != '' for k in CONTACT)


def dep_of(tags):
    """Code département d'une limite admin_level 6 (69D, 69M → 69), sinon None."""
    if tags.get('boundary') != 'administrative' or tags.get('admin_level') != '6':
        return None
    for key, rx in (('ref:INSEE', DEP_RE), ('ISO3166-2', ISO_RE)):
        m = rx.match(tags.get(key, ''))
        if m and m.group(1) in DEPS:
            return m.group(1)
    return None


def clean(v):
    return re.sub(r'[\t\r\n]+', ' ', v or '').strip()


def row(kind, oid, lat, lon, tags):
    return [kind, str(oid), '%.7f' % lat, '%.7f' % lon] + [clean(tags.get(k, '')) for k in TAG_COLUMNS]


def main(src, out_dir, stamp=''):
    os.makedirs(out_dir, exist_ok=True)
    places = []          # (type, id, lat, lon, tags)
    polys, poly_dep = [], []
    factory = osmium.geom.WKBFactory()
    skipped = {'sans_position': 0, 'relation_sans_surface': 0}
    rel_seen, rel_area = set(), set()

    fp = osmium.FileProcessor(src).with_locations().with_areas()
    for o in fp:
        if o.is_area():
            tags = dict(o.tags)
            if o.from_way():
                continue  # les chemins sont traités comme chemins (centre de l'emprise)
            dep = dep_of(tags)
            if dep:
                try:
                    polys.append(wkb.loads(factory.create_multipolygon(o), hex=True))
                    poly_dep.append(dep)
                except Exception as e:  # anneau incomplet : signalé plus bas par le contrôle des 94
                    print('limite %s (r%d) non construite : %s' % (dep, o.orig_id(), e), file=sys.stderr)
                continue
            if is_target(tags) and has_contact(tags):
                try:
                    g = wkb.loads(factory.create_multipolygon(o), hex=True)
                except Exception:
                    continue
                x0, y0, x1, y1 = g.bounds
                places.append(('relation', o.orig_id(), (y0 + y1) / 2, (x0 + x1) / 2, tags))
                rel_area.add(o.orig_id())
            continue
        if o.is_relation():
            tags = dict(o.tags)
            if is_target(tags) and has_contact(tags):
                rel_seen.add(o.id)
            continue
        tags = dict(o.tags)
        if not is_target(tags) or not has_contact(tags):
            continue
        if o.is_node():
            if o.location.valid():
                places.append(('node', o.id, o.location.lat, o.location.lon, tags))
            else:
                skipped['sans_position'] += 1
        elif o.is_way():
            pts = [(n.lat, n.lon) for n in o.nodes if n.location.valid()]
            if not pts:
                skipped['sans_position'] += 1
                continue
            lats, lons = [p[0] for p in pts], [p[1] for p in pts]
            places.append(('way', o.id, (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2, tags))
    skipped['relation_sans_surface'] = len(rel_seen - rel_area)

    missing = sorted(set(DEPS) - set(poly_dep))
    if missing:
        print('ERREUR : limites absentes pour %s' % ', '.join(missing), file=sys.stderr)
        return 2

    tree = STRtree(polys)
    by_dep = {d: [] for d in DEPS}
    outside = 0
    seen = set()
    for kind, oid, lat, lon, tags in places:
        if (kind, oid) in seen:
            continue
        seen.add((kind, oid))
        hits = tree.query(shapely.Point(lon, lat), predicate='within')
        deps = sorted({poly_dep[i] for i in hits})
        if not deps:
            outside += 1
            continue
        by_dep[deps[0]].append(row(kind, oid, lat, lon, tags))

    manifest = {
        'genere': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'extrait_osm': stamp,
        'source': 'https://download.geofabrik.de/europe/france-latest.osm.pbf',
        'licence': 'ODbL 1.0 — © contributeurs OpenStreetMap',
        'colonnes': COLUMNS,
        'lieux': sum(len(v) for v in by_dep.values()),
        'hors_departement': outside,
        'ecartes': skipped,
        'departements': {},
    }
    for d in DEPS:
        rows = sorted(by_dep[d], key=lambda r: (r[0], int(r[1])))
        body = '\t'.join(COLUMNS) + '\n' + ''.join('\t'.join(r) + '\n' for r in rows)
        data = body.encode('utf-8')
        with open(os.path.join(out_dir, d + '.tsv'), 'wb') as f:
            f.write(data)
        manifest['departements'][d] = {'lieux': len(rows), 'octets': len(data),
                                       'sha256': hashlib.sha256(data).hexdigest()}
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print('%d lieux dans %d départements, %d hors département, écartés %s'
          % (manifest['lieux'], len(DEPS), outside, skipped))
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ''))
