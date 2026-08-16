#!/usr/bin/env bash
set -euo pipefail

# Restauration à partir d'une archive produite par sauvegarde.sh.
#
# ⚠ DESTRUCTEUR : écrase la base de données et les justificatifs actuels du
# service ciblé par docker-compose.prod.yml (--clean --if-exists sur le
# pg_restore). Voir docs/06-exploitation.md — un test de restauration doit
# avoir été fait au moins une fois AVANT la mise en production, contre une
# base de test, pas la production elle-même.
#
# Usage : restauration.sh <archive.tar.gpg> --je-confirme
#
# Variables d'environnement attendues :
#   POSTGRES_USER, POSTGRES_DB — mêmes valeurs que .env.prod
#   SAUVEGARDE_GPG_PASSPHRASE  — passphrase utilisée par sauvegarde.sh

REPERTOIRE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$REPERTOIRE_SCRIPT/../../docker-compose.prod.yml"
ARCHIVE="${1:?Usage: restauration.sh <archive.tar.gpg> --je-confirme}"
CONFIRMATION="${2:-}"

: "${POSTGRES_USER:?POSTGRES_USER manquant}"
: "${POSTGRES_DB:?POSTGRES_DB manquant}"
: "${SAUVEGARDE_GPG_PASSPHRASE:?SAUVEGARDE_GPG_PASSPHRASE manquant}"

if [ "$CONFIRMATION" != "--je-confirme" ]; then
    echo "Cette opération ÉCRASE la base de données et les justificatifs actuels" >&2
    echo "de la cible pointée par docker-compose.prod.yml." >&2
    echo "Relancez avec --je-confirme pour continuer :" >&2
    echo "  $0 \"$ARCHIVE\" --je-confirme" >&2
    exit 1
fi

if [ ! -f "$ARCHIVE" ]; then
    echo "Archive introuvable : $ARCHIVE" >&2
    exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[restauration] déchiffrement..."
gpg --batch --yes --passphrase "$SAUVEGARDE_GPG_PASSPHRASE" \
    --decrypt --output "$TMP/archive.tar" "$ARCHIVE"

echo "[restauration] extraction..."
tar xf "$TMP/archive.tar" -C "$TMP"

DUMP_FICHIER="$(find "$TMP" -maxdepth 1 -name 'gep-*.dump' | head -n1)"
JUSTIFICATIFS_FICHIER="$(find "$TMP" -maxdepth 1 -name 'justificatifs-*.tar.gz' | head -n1)"

if [ -z "$DUMP_FICHIER" ]; then
    echo "Aucun dump Postgres (gep-*.dump) dans l'archive — abandon." >&2
    exit 1
fi

echo "[restauration] base de données (--clean --if-exists : écrase l'existant)..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < "$DUMP_FICHIER"

if [ -n "$JUSTIFICATIFS_FICHIER" ]; then
    echo "[restauration] justificatifs (remplace le contenu actuel du volume)..."
    docker compose -f "$COMPOSE_FILE" exec -T api sh -c \
        'rm -rf /donnees/justificatifs/* && tar xzf - -C /donnees/justificatifs' \
        < "$JUSTIFICATIFS_FICHIER"
else
    echo "[restauration] pas d'archive de justificatifs dans ce backup, ignoré."
fi

echo "[restauration] terminée."
echo "Vérifiez l'application (connexion, quelques écrans clés), puis :"
echo "  docker compose -f docker-compose.prod.yml restart api"
