#!/usr/bin/env bash
set -euo pipefail

# Sauvegarde quotidienne : dump Postgres + justificatifs, chiffrés (gpg
# symétrique), conservés 30 jours, copiés hors machine. Voir
# docs/06-exploitation.md pour la procédure d'exploitation complète et
# docs/05-deploiement.md pour l'installation du cron qui appelle ce script.
#
# « La sauvegarde n'est pas optionnelle » (docs/01-architecture.md §8) : un
# test de restauration (infra/scripts/restauration.sh) doit avoir été fait au
# moins une fois avant la mise en production. Une sauvegarde jamais restaurée
# n'est pas une sauvegarde.
#
# Variables d'environnement attendues :
#   POSTGRES_USER, POSTGRES_DB        — mêmes valeurs que .env.prod
#   SAUVEGARDE_GPG_PASSPHRASE         — passphrase du chiffrement symétrique gpg
#   SAUVEGARDE_DEST (optionnel)       — répertoire local des archives (défaut : infra/../sauvegardes)
#   SAUVEGARDE_RETENTION_JOURS        — défaut 30
#   SAUVEGARDE_RSYNC_DEST (optionnel) — destination rsync hors machine (ex. user@hote:/chemin)

REPERTOIRE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$REPERTOIRE_SCRIPT/../../docker-compose.prod.yml"
DEST="${SAUVEGARDE_DEST:-$REPERTOIRE_SCRIPT/../../sauvegardes}"
RETENTION_JOURS="${SAUVEGARDE_RETENTION_JOURS:-30}"
HORODATAGE="$(date -u +%Y-%m-%dT%H-%M-%SZ)"

: "${POSTGRES_USER:?POSTGRES_USER manquant}"
: "${POSTGRES_DB:?POSTGRES_DB manquant}"
: "${SAUVEGARDE_GPG_PASSPHRASE:?SAUVEGARDE_GPG_PASSPHRASE manquant — voir docs/06-exploitation.md}"

mkdir -p "$DEST"

echo "[sauvegarde] dump Postgres (format personnalisé, compressé)..."
DUMP_FICHIER="$DEST/gep-${HORODATAGE}.dump"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$DUMP_FICHIER"

echo "[sauvegarde] archive des justificatifs (depuis le conteneur api, pas de dépendance"
echo "  au nom du volume Docker)..."
JUSTIFICATIFS_FICHIER="$DEST/justificatifs-${HORODATAGE}.tar.gz"
docker compose -f "$COMPOSE_FILE" exec -T api \
    tar czf - -C /donnees/justificatifs . > "$JUSTIFICATIFS_FICHIER"

echo "[sauvegarde] archive combinée + chiffrement gpg (symétrique, AES256)..."
ARCHIVE="$DEST/gep-${HORODATAGE}.tar"
tar cf "$ARCHIVE" -C "$DEST" "$(basename "$DUMP_FICHIER")" "$(basename "$JUSTIFICATIFS_FICHIER")"
rm -f "$DUMP_FICHIER" "$JUSTIFICATIFS_FICHIER"

gpg --batch --yes --passphrase "$SAUVEGARDE_GPG_PASSPHRASE" --symmetric --cipher-algo AES256 \
    --output "${ARCHIVE}.gpg" "$ARCHIVE"
rm -f "$ARCHIVE"

echo "[sauvegarde] archive chiffrée : ${ARCHIVE}.gpg"

echo "[sauvegarde] purge des archives de plus de ${RETENTION_JOURS} jours..."
find "$DEST" -name "gep-*.tar.gpg" -mtime "+${RETENTION_JOURS}" -delete

if [ -n "${SAUVEGARDE_RSYNC_DEST:-}" ]; then
    echo "[sauvegarde] copie hors machine (rsync) vers ${SAUVEGARDE_RSYNC_DEST}..."
    rsync -az "${ARCHIVE}.gpg" "$SAUVEGARDE_RSYNC_DEST"
else
    echo "[sauvegarde] ATTENTION : SAUVEGARDE_RSYNC_DEST n'est pas défini — cette" >&2
    echo "  sauvegarde reste UNIQUEMENT sur cette machine. Un incident sur ce serveur" >&2
    echo "  (disque, incendie, vol) emporterait la sauvegarde avec les données." >&2
    echo "  Configurez une copie hors machine avant la mise en production" >&2
    echo "  (voir docs/06-exploitation.md)." >&2
    # TODO : si rsync vers un autre serveur n'est pas disponible, utiliser
    # rclone vers un stockage objet (S3, Backblaze B2, etc.) :
    #   rclone copy "${ARCHIVE}.gpg" "remote:gep-sauvegardes/"
fi

echo "[sauvegarde] terminée."
