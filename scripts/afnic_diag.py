"""Diagnostic du fichier A de l'Afnic (noms de domaine en .fr) : format réel, encodage, colonnes, volumes.

Usage : python3 -I scripts/afnic_diag.py <fichier.zip> <rapport.txt>
Lit le ZIP en flux (aucune décompression sur disque). N'écrit que des comptes et quelques exemples de domaines
de personnes morales (les domaines des particuliers ne sont jamais recopiés).
"""
import collections
import io
import sys
import zipfile


def guess_encoding(raw):
    for enc in ('utf-8', 'cp1252'):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    return 'latin-1'


def main(src, dst):
    out = []
    p = out.append
    z = zipfile.ZipFile(src)
    for i in z.infolist():
        p('membre : %s | %d octets compressés | %d octets' % (i.filename, i.compress_size, i.file_size))
    member = max(z.infolist(), key=lambda i: i.file_size)
    with z.open(member) as f:
        head = f.read(4 * 1024 * 1024)
    enc = guess_encoding(head[: head.rfind(b'\n')])
    p('encodage probable (4 premiers Mo) : %s' % enc)
    p('BOM UTF-8 : %s' % head.startswith(b'\xef\xbb\xbf'))
    p('fins de ligne CRLF : %s' % (b'\r\n' in head[:10000]))
    first = head.split(b'\n', 1)[0].decode(enc, 'replace').lstrip('﻿').rstrip('\r')
    sep = max([';', ',', '\t', '|'], key=first.count)
    p('séparateur : %r' % sep)
    cols = first.split(sep)
    p('en-tête (%d colonnes) :' % len(cols))
    for n, c in enumerate(cols):
        p('  %2d %s' % (n, c))

    def col(*names):
        low = [c.strip().lower() for c in cols]
        for name in names:
            for n, c in enumerate(low):
                if name in c:
                    return n
        return None

    i_dom = col('nom de domaine', 'domaine')
    i_type = col('type du titulaire', 'type titulaire')
    i_pays = col('pays titulaire')
    i_dep = col('departement titulaire', 'département titulaire')
    i_ret = col('retrait')
    i_crea = col('date de cr')
    i_sous = col('sous domaine', 'sous-domaine')
    p('colonnes repérées : domaine=%s type=%s pays=%s dep=%s retrait=%s creation=%s sous=%s'
      % (i_dom, i_type, i_pays, i_dep, i_ret, i_crea, i_sous))

    widths = collections.Counter()
    types = collections.Counter()
    pays = collections.Counter()
    deps_actifs_pm = collections.Counter()
    sous = collections.Counter()
    ret_vides = 0
    actifs_pm_fr = 0
    crea_min, crea_max = None, None
    ret_exemples = collections.Counter()
    exemples = collections.defaultdict(list)
    lignes = 0
    bruts = []
    with z.open(member) as f:
        t = io.TextIOWrapper(f, encoding=enc, errors='replace', newline='')
        next(t)
        for line in t:
            line = line.rstrip('\r\n')
            if not line:
                continue
            lignes += 1
            v = line.split(sep)
            widths[len(v)] += 1
            if len(v) != len(cols):
                continue

            def g(i):
                return v[i].strip().strip('"') if i is not None else ''

            ty = g(i_type)
            types[ty] += 1
            pa = g(i_pays)
            pays[pa if pa in ('FR', '') else 'autre'] += 1
            if i_sous is not None:
                sous[g(i_sous)] += 1
            rt = g(i_ret)
            if rt == '':
                ret_vides += 1
            elif len(ret_exemples) < 5:
                ret_exemples[rt] += 1
            cr = g(i_crea)
            if cr:
                crea_min = cr if crea_min is None or cr < crea_min else crea_min
                crea_max = cr if crea_max is None or cr > crea_max else crea_max
            morale = 'morale' in ty.lower() or ty.upper() in ('PM', 'M')
            if rt == '' and morale and pa == 'FR':
                actifs_pm_fr += 1
                d = g(i_dep)
                deps_actifs_pm[d] += 1
                if d in ('69', '75', '17') and len(exemples[d]) < 15:
                    exemples[d].append(g(i_dom))
            if lignes <= 3:
                bruts.append(line)
    p('lignes de données : %d' % lignes)
    p('nombre de champs par ligne : %s' % dict(widths.most_common(5)))
    p('3 premières lignes brutes (type de titulaire masqué si particulier) :')
    for b in bruts:
        p('  ' + (b if 'morale' in b.lower() else '[ligne de particulier non recopiée]'))
    p('type du titulaire : %s' % dict(types.most_common(10)))
    p('pays titulaire : %s' % dict(pays))
    p('sous-domaine : %s' % dict(sous.most_common(6)))
    p('date de retrait vide (domaine actif) : %d' % ret_vides)
    p('exemples de date de retrait : %s' % list(ret_exemples))
    p('date de création : de %s à %s' % (crea_min, crea_max))
    p('actifs, personne morale, pays FR : %d' % actifs_pm_fr)
    p('départements (actifs, personne morale, FR) : %d valeurs distinctes' % len(deps_actifs_pm))
    for d, n in sorted(deps_actifs_pm.items()):
        p('  %r %d' % (d, n))
    for d in ('17', '69', '75'):
        p('exemples %s : %s' % (d, ', '.join(exemples[d])))
    open(dst, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('\n'.join(out[:60]))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
