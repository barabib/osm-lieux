# osm-lieux

Lieux OpenStreetMap avec site ou e-mail, par département. © contributeurs OpenStreetMap, licence ODbL.

## Contenu

Une fois par mois, la tâche `.github/workflows/lieux.yml` :

1. télécharge l'extrait France de Geofabrik (`france-latest.osm.pbf`) et contrôle son md5 ;
2. garde avec `osmium tags-filter` les restaurants, bars, cafés, hôtels, campings, gîtes, cavistes, épiceries, traiteurs, domaines et brasseries, ainsi que les limites des départements ;
3. ne garde que les lieux qui ont un site ou un e-mail (`scripts/extraire.py`), les range par département (position du nœud, ou centre de l'emprise pour un chemin ou une surface) et écrit un fichier par département de métropole, de 01 à 95. La Corse est exclue : 94 fichiers au total ;
4. publie les fichiers en pièces jointes d'une release, puis garde les 3 dernières.

Adresse d'un fichier : `https://github.com/barabib/osm-lieux/releases/latest/download/69.tsv`

Format : celui de la sortie CSV d'Overpass, avec des tabulations et une ligne d'en-tête :
`@type @id @lat @lon name addr:postcode addr:city website contact:website url email contact:email ref:FR:SIRET`.
`manifest.json` donne la date de l'extrait, le nombre de lieux et l'empreinte sha256 de chaque fichier. `etat.json` garde le bilan du dernier passage : durées, tailles et lieux par département.

## Licence

Les données viennent d'OpenStreetMap. © contributeurs OpenStreetMap, sous licence [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Les fichiers publiés ici sont une base dérivée, sous la même licence.

## Banc

`bash banc/banc.sh` : fabrique un petit fichier OSM, lui applique le même filtre et la même extraction, puis vérifie le résultat. Il n'utilise pas le réseau. Prérequis : `osmium-tool`, puis `pip install osmium==4.3.2 shapely==2.2.0`.
