"""Noms de domaine .fr actifs (fichier A de l'Afnic) en empreintes, pour derf_prospect.

Usage : python3 -I scripts/domaines.py <fichier A.zip> <dossier de sortie> <mois AAAAMM>

Le fichier A ne donne ni titulaire ni département (colonnes vides sur plus de 99,9 % des lignes, diagnostic du 27/11/2026) :
le module ne peut donc que vérifier si un nom de domaine qu'il construit à partir du nom d'un établissement existe.
On ne publie pas la liste des domaines : seulement une empreinte de chacun (SHA-1 du libellé sans « .fr », en minuscules),
répartie en 16 fichiers selon le premier chiffre hexadécimal de l'empreinte. Chaque fichier : enregistrements de 7 octets
(octets 1 à 7 de l'empreinte), triés, sans séparateur. Le module recherche par dichotomie.

Gardés : domaine directement sous .fr (pas asso.fr, com.fr…), pas de date de retrait du WHOIS, libellé ASCII [a-z0-9-].
"""
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile

REC = 7
LABEL = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')


def main(src, out, mois):
    os.makedirs(out, exist_ok=True)
    z = zipfile.ZipFile(src)
    member = max(z.infolist(), key=lambda i: i.file_size)
    buckets = [[] for _ in range(16)]
    n = {'lignes': 0, 'actifs': 0, 'gardes': 0, 'sous_domaine': 0, 'retires': 0, 'non_ascii': 0}
    with z.open(member) as f:
        t = io.TextIOWrapper(f, encoding='utf-8', errors='replace', newline='')
        head = [c.strip().strip('"').lower() for c in next(t).rstrip('\r\n').split(';')]
        i_dom = head.index('nom de domaine')
        i_sous = head.index('sous domaine')
        i_ret = [k for k, c in enumerate(head) if 'retrait' in c][0]
        for line in t:
            v = line.rstrip('\r\n').split(';')
            if len(v) != len(head):
                continue
            n['lignes'] += 1
            if v[i_ret].strip().strip('"') != '':
                n['retires'] += 1
                continue
            n['actifs'] += 1
            if v[i_sous].strip().strip('"').lower() != 'fr':
                n['sous_domaine'] += 1
                continue
            dom = v[i_dom].strip().strip('"').lower()
            label = dom[:-3] if dom.endswith('.fr') else ''
            if not LABEL.match(label):
                n['non_ascii'] += 1
                continue
            h = hashlib.sha1(label.encode('ascii')).digest()
            buckets[h[0] >> 4].append(h[1:1 + REC])
            n['gardes'] += 1
    files = {}
    for b in range(16):
        recs = sorted(set(buckets[b]))
        name = 'fr-%x.bin' % b
        data = b''.join(recs)
        open(os.path.join(out, name), 'wb').write(data)
        files[name] = {'enregistrements': len(recs), 'octets': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    manifest = {
        'genere': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'mois_afnic': mois,
        'source': member.filename,
        'empreinte': 'sha1(libelle sans .fr, minuscules), premier chiffre hexadecimal = fichier, octets 1 a %d = enregistrement' % REC,
        'enregistrement_octets': REC,
        'comptes': n,
        'fichiers': files,
    }
    json.dump(manifest, open(os.path.join(out, 'domaines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in manifest.items() if k != 'fichiers'}, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
