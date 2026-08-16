"""Schémas Pydantic — entrée et sortie du module auth."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr

from app.modules.auth.models import RoleUtilisateur


class LoginRequete(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    email: str
    role: RoleUtilisateur
    actif: bool


class LoginReponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurPublic


class AccessTokenReponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DeconnexionPartoutRequete(BaseModel):
    utilisateur_id: int
