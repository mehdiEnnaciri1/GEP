"""Service d'authentification — frontière transactionnelle du module auth.

Ignore HTTP : lève `AuthentificationInvalide` (401) en cas d'échec, jamais
`HTTPException`. Le router traduit et gère les cookies.

Chaque méthode commite elle-même son unité de travail — y compris sur le
chemin d'échec de `authentifier` : la tentative ratée doit rester journalisée
même si la méthode lève ensuite. Si le commit était laissé au router (après le
retour de la méthode), l'entrée d'audit d'un échec de connexion serait perdue,
puisque l'exception empêcherait jamais d'atteindre ce commit.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthentificationInvalide, RessourceIntrouvable
from app.core.security import (
    creer_access_token,
    creer_refresh_token,
    decoder_token,
    verifier_mot_de_passe,
)
from app.modules.audit.service import journaliser
from app.modules.auth.models import Utilisateur
from app.modules.auth.repository import UtilisateurRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._utilisateurs = UtilisateurRepository(session)

    async def authentifier(
        self, email: str, mot_de_passe: str, adresse_ip: str | None
    ) -> tuple[str, str, Utilisateur]:
        utilisateur = await self._utilisateurs.get_by_email(email)
        mot_de_passe_correct = verifier_mot_de_passe(
            mot_de_passe, utilisateur.mot_de_passe_hash if utilisateur else None
        )

        if utilisateur is None or not utilisateur.actif or not mot_de_passe_correct:
            await journaliser(
                self._session,
                action="CONNEXION_ECHOUEE",
                entite="utilisateur",
                entite_id=utilisateur.id if utilisateur else None,
                utilisateur_id=utilisateur.id if utilisateur else None,
                apres={"email": email},
                adresse_ip=adresse_ip,
            )
            await self._session.commit()
            raise AuthentificationInvalide("Email ou mot de passe incorrect.")

        await self._utilisateurs.marquer_derniere_connexion(utilisateur)
        await journaliser(
            self._session,
            action="CONNEXION",
            entite="utilisateur",
            entite_id=utilisateur.id,
            utilisateur_id=utilisateur.id,
            adresse_ip=adresse_ip,
        )

        access_token = creer_access_token(utilisateur.id, utilisateur.role.value)
        refresh_token = creer_refresh_token(utilisateur.id)
        await self._session.commit()
        return access_token, refresh_token, utilisateur

    async def rafraichir(self, refresh_token: str) -> str:
        charge = decoder_token(refresh_token, type_attendu="refresh")
        utilisateur = await self._utilisateurs.get_by_id(int(charge["sub"]))

        if utilisateur is None or not utilisateur.actif:
            raise AuthentificationInvalide("Authentification requise.")

        # `iat` est un entier de secondes (norme JWT), tronqué par rapport à
        # `tokens_invalides_avant` (microseconde) — comparer le premier tel
        # quel contre le second, sans arrondir ce dernier, reste correct
        # pour révoquer un jeton ANTÉRIEUR (floor(iat) <= iat < révocation
        # implique floor(iat) < révocation, quelle que soit la seconde).
        # L'arrondir aurait affaibli cette garantie pour gagner, en échange,
        # un cas bien plus rare et bien moins grave : une connexion émise
        # dans la MÊME seconde qu'une révocation peut exceptionnellement
        # essuyer un rafraîchissement refusé — l'utilisateur se reconnecte,
        # rien de plus. Mieux vaut over-révoquer que sous-révoquer.
        emis_le = datetime.fromtimestamp(charge["iat"], tz=UTC)
        if (
            utilisateur.tokens_invalides_avant is not None
            and emis_le < utilisateur.tokens_invalides_avant
        ):
            raise AuthentificationInvalide("Authentification requise.")

        return creer_access_token(utilisateur.id, utilisateur.role.value)

    async def deconnecter(self, utilisateur: Utilisateur, adresse_ip: str | None) -> None:
        utilisateur.tokens_invalides_avant = datetime.now(UTC)

        await journaliser(
            self._session,
            action="DECONNEXION",
            entite="utilisateur",
            entite_id=utilisateur.id,
            utilisateur_id=utilisateur.id,
            adresse_ip=adresse_ip,
        )
        await self._session.commit()

    async def deconnecter_partout(
        self, utilisateur_id: int, initiateur_id: int, adresse_ip: str | None
    ) -> None:
        """Révocation globale (§10) : tout refresh token de `utilisateur_id`
        émis avant maintenant devient inutilisable, même sur un autre
        appareil — utile en cas de perte/vol d'un poste ou de départ d'un
        employé."""
        utilisateur = await self._utilisateurs.get_by_id(utilisateur_id)
        if utilisateur is None:
            raise RessourceIntrouvable(f"Utilisateur {utilisateur_id} introuvable.")

        utilisateur.tokens_invalides_avant = datetime.now(UTC)

        await journaliser(
            self._session,
            action="MODIFICATION",
            entite="utilisateur",
            entite_id=utilisateur.id,
            utilisateur_id=initiateur_id,
            apres={"tokens_invalides_avant": utilisateur.tokens_invalides_avant.isoformat()},
            adresse_ip=adresse_ip,
        )
        await self._session.commit()
