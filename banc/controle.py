"""Contrôles du résultat du banc (echantillon.osm). Sortie non nulle au premier écart."""
import json
import os
import sys

out = sys.argv[1]
HEAD = '@type\t@id\t@lat\t@lon\tname\taddr:postcode\taddr:city\twebsite\tcontact:website\turl\temail\tcontact:email\tref:FR:SIRET'
ok = 0


def check(cond, label):
    global ok
    if not cond:
        print('ÉCHEC : ' + label)
        sys.exit(1)
    ok += 1


def rows(dep):
    with open(os.path.join(out, dep + '.tsv'), encoding='utf-8') as f:
        lines = f.read().split('\n')
    check(lines[0] == HEAD, dep + ' : en-tête identique à Overpass')
    check(lines[-1] == '', dep + ' : fin de ligne finale')
    return [l.split('\t') for l in lines[1:-1]]


files = sorted(os.listdir(out))
check(files == ['01.tsv', '69.tsv', 'manifest.json'], 'fichiers produits : %s' % files)

r69 = rows('69')
ids = [(r[0], r[1]) for r in r69]
check(ids == [('node', '1'), ('node', '3'), ('node', '6'), ('relation', '20')], '69 : lieux attendus (69D + 69M), triés : %s' % ids)
check(all(len(r) == 13 for r in r69), '69 : 13 colonnes par ligne')
by = {r[1]: r for r in r69}
check(by['1'][4:8] == ['Chez Paul', '69002', 'Lyon', 'https://chezpaul.fr'], '69 : nœud 1 complet')
check(by['1'][2:4] == ['45.7000000', '4.8000000'], '69 : position à 7 décimales')
check(by['3'][4] == 'Le Zinc' and by['3'][11] == 'contact@lezinc.fr', '69 : tabulation du nom remplacée, contact:email gardé')
check(by['6'][7] == 'https://domaine.fr;https://autre.fr' and by['6'][12] == '12345678900011', '69 : valeurs multiples et SIRET bruts')
check(by['20'][2:4] == ['45.6500000', '4.1500000'] and by['20'][4] == 'Grand Resto', '69 : relation multipolygone au centre de l\'emprise')

r01 = rows('01')
check([(r[0], r[1]) for r in r01] == [('way', '10')], '01 : hôtel (chemin) seul')
check(r01[0][2:4] == ['46.1500000', '5.1500000'] and r01[0][10] == 'info@hotel.fr', '01 : centre de l\'emprise et e-mail')

with open(os.path.join(out, 'manifest.json'), encoding='utf-8') as f:
    m = json.load(f)
check(m['lieux'] == 5, 'manifeste : 5 lieux')
check(m['hors_departement'] == 2, 'manifeste : 2 lieux hors département (Corse exclue, Allemagne)')
check(m['extrait_osm'] == '2026-11-26T00:00:00Z', 'manifeste : horodatage de l\'extrait')
check(m['departements']['69']['lieux'] == 4 and m['departements']['01']['lieux'] == 1, 'manifeste : comptes par département')
print('banc osm-lieux : %d/%d contrôles' % (ok, ok))
