"""Stockage des justificatifs de charge sur disque — voir
`reglages.chemin_justificatifs` (volume Docker dédié, jamais dans le dépôt ;
voir docker-compose.yml, service `donnees_justificatifs`).

Le type MIME est détecté sur les octets réels du fichier (signature binaire,
« magic bytes »), jamais sur l'extension du nom ni le Content-Type déclaré
par le client HTTP : les deux sont falsifiables par qui envoie la requête.
Seuls JPEG, PNG et PDF sont acceptés — trois signatures suffisent, pas besoin
d'une dépendance externe (python-magic/libmagic) pour ça.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import obtenir_reglages
from app.core.exceptions import ValidationMetier

_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
)


def detecter_type_mime(contenu: bytes) -> str | None:
    """`None` si `contenu` ne correspond à aucune signature JPEG/PNG/PDF connue."""
    for signature, type_mime in _SIGNATURES:
        if contenu.startswith(signature):
            return type_mime
    return None


def _resoudre(chemin_relatif: str, base_dir: Path) -> Path:
    """Résout `chemin_relatif` sous `base_dir` et refuse tout chemin qui en
    sortirait après résolution (`..`, chemin absolu détourné, etc.) — un
    path traversal ne doit jamais pouvoir faire écrire ou lire en dehors du
    répertoire de stockage, quelle que soit l'origine du nom de fichier."""

    base_dir = base_dir.resolve()
    chemin_absolu = (base_dir / chemin_relatif).resolve()
    if chemin_absolu != base_dir and base_dir not in chemin_absolu.parents:
        raise ValidationMetier(f"Chemin de fichier invalide : {chemin_relatif!r}.")
    return chemin_absolu


def sauvegarder(contenu: bytes, chemin_relatif: str, *, base_dir: Path | None = None) -> str:
    """Écrit `contenu` à `chemin_relatif` sous le répertoire de stockage et
    retourne le type MIME détecté. Lève `ValidationMetier` si :
    - le chemin résolu sort du répertoire de stockage (path traversal) ;
    - la taille dépasse `reglages.taille_max_fichier_mo` ;
    - le contenu n'est ni un JPEG, ni un PNG, ni un PDF.

    `base_dir` : injectable pour les tests (répertoire temporaire), sinon
    `reglages.chemin_justificatifs`.
    """

    reglages = obtenir_reglages()
    taille_max_octets = reglages.taille_max_fichier_mo * 1024 * 1024
    if len(contenu) > taille_max_octets:
        raise ValidationMetier(
            f"Fichier trop volumineux ({len(contenu)} octets) — "
            f"maximum {reglages.taille_max_fichier_mo} Mo."
        )

    type_mime = detecter_type_mime(contenu)
    if type_mime is None:
        raise ValidationMetier("Type de fichier non reconnu — JPEG, PNG ou PDF uniquement.")

    chemin_absolu = _resoudre(chemin_relatif, base_dir or Path(reglages.chemin_justificatifs))
    chemin_absolu.parent.mkdir(parents=True, exist_ok=True)
    chemin_absolu.write_bytes(contenu)
    return type_mime


def lire(chemin_relatif: str, *, base_dir: Path | None = None) -> bytes:
    """Lit le fichier à `chemin_relatif` — mêmes garanties de chemin que
    `sauvegarder` (jamais en dehors du répertoire de stockage)."""

    reglages = obtenir_reglages()
    chemin_absolu = _resoudre(chemin_relatif, base_dir or Path(reglages.chemin_justificatifs))
    return chemin_absolu.read_bytes()
