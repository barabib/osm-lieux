"""Banc hors ligne de scripts/domaines.py : petit fichier A au format réel (diagnostic du 27/11/2026), contrôles."""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
HEAD = '"Nom de domaine";"Pays BE";"Departement BE";"Ville BE";"Nom BE";"Sous domaine";"Type du titulaire";"Pays titulaire";"Departement titulaire";"Domaine IDN";"Date de création";"Date de retrait du WHOIS"'
ROWS = [
    ('lebistrotdupont.fr', 'fr', '0', ''),
    ('le-bistrot-dupont.fr', 'fr', '0', ''),
    ('vieuxresto.fr', 'fr', '0', '05-12-2025'),
    ('clubdefoot.asso.fr', 'asso.fr', '0', ''),
    ('cafédelagare.fr', 'fr', '1', ''),
    ('LaCave69.fr', 'fr', '0', ''),
]
ok = True


def check(cond, what):
    global ok
    print(('OK   ' if cond else 'ECHEC ') + what)
    ok = ok and cond


def find(out, label, rec):
    h = hashlib.sha1(label.encode()).digest()
    data = open(os.path.join(out, 'fr-%x.bin' % (h[0] >> 4)), 'rb').read()
    key = h[1:1 + rec]
    lo, hi = 0, len(data) // rec
    while lo < hi:
        mid = (lo + hi) // 2
        v = data[mid * rec:(mid + 1) * rec]
        if v == key:
            return True
        if v < key:
            lo = mid + 1
        else:
            hi = mid
    return False


with tempfile.TemporaryDirectory() as t:
    csv = HEAD + '\n' + '\n'.join('"%s";"FR";"59";"ROUBAIX";"OVH";"%s";"";"";"";"%s";"12-03-2010";"%s"' % r for r in ROWS) + '\n'
    with zipfile.ZipFile(os.path.join(t, 'a.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('202610_OPENDATA_A-NomsDeDomaineEnPointFr.csv', csv.encode('utf-8'))
    out = os.path.join(t, 'out')
    subprocess.run([sys.executable, '-I', os.path.join(ICI, '..', 'scripts', 'domaines.py'), os.path.join(t, 'a.zip'), out, '202610'], check=True)
    m = json.load(open(os.path.join(out, 'domaines.json'), encoding='utf-8'))
    c = m['comptes']
    check(c == {'lignes': 6, 'actifs': 5, 'gardes': 3, 'sous_domaine': 1, 'retires': 1, 'non_ascii': 1}, 'comptes %s' % c)
    check(len(m['fichiers']) == 16, '16 fichiers')
    check(sum(f['enregistrements'] for f in m['fichiers'].values()) == 3, '3 empreintes')
    for name, f in m['fichiers'].items():
        data = open(os.path.join(out, name), 'rb').read()
        check(hashlib.sha256(data).hexdigest() == f['sha256'] and len(data) == f['octets'], 'sha256 et taille ' + name) if f['octets'] else None
    for label, want in [('lebistrotdupont', True), ('le-bistrot-dupont', True), ('lacave69', True), ('vieuxresto', False),
                        ('clubdefoot', False), ('absent', False), ('lebistrotdupon', False)]:
        check(find(out, label, m['enregistrement_octets']) is want, 'recherche %s -> %s' % (label, want))
sys.exit(0 if ok else 1)
