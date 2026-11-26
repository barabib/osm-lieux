#!/usr/bin/env bash
# Banc hors ligne : petit fichier OSM fabriqué à la main, même filtre que la tâche, contrôles du résultat.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

osmium cat "$ICI/echantillon.osm" -o "$T/france.pbf"
FILTRE="$(sed -n 's/^ *FILTRE: //p' "$ICI/../.github/workflows/lieux.yml" | tr -d '"')"
# shellcheck disable=SC2086
osmium tags-filter "$T/france.pbf" $FILTRE -o "$T/lieux.pbf"
OSM_LIEUX_DEPS=01,69 python3 -I "$ICI/../scripts/extraire.py" "$T/lieux.pbf" "$T/out" "2026-11-26T00:00:00Z"
python3 -I "$ICI/controle.py" "$T/out"
