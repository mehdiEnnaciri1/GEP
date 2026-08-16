"""Endpoints HTTP du module rapports. Les permissions suivent celles des
données exportées (§6.6) : élèves/paiements/impayés/reçu — ADMIN et CAISSIER ;
paie et récapitulatif (qui exposent charges/paie/bénéfice) — ADMIN seul."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import exige_role
from app.db.session import get_session
from app.modules.auth.models import RoleUtilisateur, Utilisateur
from app.modules.rapports.service import RapportService

router = APIRouter(prefix="/rapports", tags=["rapports"])

_LECTURE = exige_role(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
_ADMIN_SEUL = exige_role(RoleUtilisateur.ADMIN)

_MEDIA_PDF = "application/pdf"
_MEDIA_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _fichier(contenu: bytes, nom_fichier: str, media_type: str) -> Response:
    return Response(
        content=contenu,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get("/eleves/pdf")
async def rapport_eleves_pdf(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).pdf_liste_eleves()
    return _fichier(contenu, "liste-eleves.pdf", _MEDIA_PDF)


@router.get("/eleves/excel")
async def rapport_eleves_excel(
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).excel_liste_eleves()
    return _fichier(contenu, "liste-eleves.xlsx", _MEDIA_EXCEL)


@router.get("/paiements/pdf")
async def rapport_paiements_pdf(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).pdf_liste_paiements(periode)
    return _fichier(contenu, f"paiements-{periode}.pdf", _MEDIA_PDF)


@router.get("/paiements/excel")
async def rapport_paiements_excel(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).excel_liste_paiements(periode)
    return _fichier(contenu, f"paiements-{periode}.xlsx", _MEDIA_EXCEL)


@router.get("/impayes/pdf")
async def rapport_impayes_pdf(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).pdf_liste_impayes(periode)
    return _fichier(contenu, f"impayes-{periode}.pdf", _MEDIA_PDF)


@router.get("/impayes/excel")
async def rapport_impayes_excel(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).excel_liste_impayes(periode)
    return _fichier(contenu, f"impayes-{periode}.xlsx", _MEDIA_EXCEL)


@router.get("/paie/pdf")
async def rapport_paie_pdf(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> Response:
    contenu = await RapportService(session).pdf_paie_professeurs(periode)
    return _fichier(contenu, f"paie-{periode}.pdf", _MEDIA_PDF)


@router.get("/paie/excel")
async def rapport_paie_excel(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> Response:
    contenu = await RapportService(session).excel_paie_professeurs(periode)
    return _fichier(contenu, f"paie-{periode}.xlsx", _MEDIA_EXCEL)


@router.get("/recapitulatif/pdf")
async def rapport_recapitulatif_pdf(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> Response:
    contenu = await RapportService(session).pdf_recapitulatif(periode)
    return _fichier(contenu, f"recapitulatif-{periode}.pdf", _MEDIA_PDF)


@router.get("/recapitulatif/excel")
async def rapport_recapitulatif_excel(
    periode: str,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_ADMIN_SEUL),
) -> Response:
    contenu = await RapportService(session).excel_recapitulatif(periode)
    return _fichier(contenu, f"recapitulatif-{periode}.xlsx", _MEDIA_EXCEL)


@router.get("/recu/{paiement_id}/pdf")
async def rapport_recu_pdf(
    paiement_id: int,
    session: AsyncSession = Depends(get_session),
    _utilisateur: Utilisateur = Depends(_LECTURE),
) -> Response:
    contenu = await RapportService(session).pdf_recu(paiement_id)
    return _fichier(contenu, f"recu-{paiement_id}.pdf", _MEDIA_PDF)
