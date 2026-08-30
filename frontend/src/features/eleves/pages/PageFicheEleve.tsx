import { useState } from 'react'

import { Link, useParams } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useChangerStatutEleve,
  useEleve,
  useModifierEngagement,
} from '@/features/eleves/hooks/useEleves'
import type { StatutEleve } from '@/features/eleves/types'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { dirhamsVersCentimes, formaterMontant } from '@/lib/money'

const PROCHAIN_STATUT: Record<StatutEleve, StatutEleve | null> = {
  ACTIF: 'SUSPENDU',
  SUSPENDU: 'ACTIF',
  ARCHIVE: null,
}

function moisProchain(): string {
  const maintenant = new Date()
  const prochain = new Date(maintenant.getFullYear(), maintenant.getMonth() + 1, 1)
  return `${prochain.getFullYear()}-${String(prochain.getMonth() + 1).padStart(2, '0')}`
}

export function PageFicheEleve() {
  const { id } = useParams<{ id: string }>()
  const eleveId = id ? Number(id) : undefined
  const { data: eleve, isLoading } = useEleve(eleveId)
  const { data: matieres } = useMatieres()
  const changerStatut = useChangerStatutEleve()
  const modifierEngagement = useModifierEngagement()

  const [panneauOuvert, setPanneauOuvert] = useState(false)
  const [periodeApplication, setPeriodeApplication] = useState(moisProchain())
  const [estPack, setEstPack] = useState(false)
  const [reductionActive, setReductionActive] = useState(false)
  const [reductionDh, setReductionDh] = useState('')
  const [matiereIds, setMatiereIds] = useState<number[]>([])
  const [erreur, setErreur] = useState<string | null>(null)

  if (isLoading || !eleve) {
    return <p className="p-6 text-sm text-muted-foreground">Chargement…</p>
  }

  const nomMatiere = (matiereId: number) =>
    matieres?.find((m) => m.id === matiereId)?.libelle ?? `Matière #${matiereId}`

  const inscriptionsActives = eleve.inscriptions.filter((i) => i.date_fin === null)
  // Réduction : montant fixe, indépendant des matières. Sinon (NORMAL ou
  // PACK) : somme des inscriptions — pour le pack, chaque inscription porte
  // déjà le tarif pack fractionné, la somme retombe pile sur le forfait.
  const totalMensuel =
    eleve.reduction_mensuelle_cents ??
    inscriptionsActives.reduce((somme, i) => somme + i.tarif_mensuel_cents, 0)

  const prochainStatut = PROCHAIN_STATUT[eleve.statut]
  const matieresActives = matieres?.filter((m) => m.actif) ?? []

  const gererErreur = (err: unknown) =>
    setErreur(err instanceof ErreurApi ? err.message : "Erreur lors de l'opération.")

  const ouvrirPanneau = () => {
    setErreur(null)
    setPeriodeApplication(moisProchain())
    setEstPack(eleve.est_pack)
    setReductionActive(eleve.reduction_mensuelle_cents !== null)
    setReductionDh(
      eleve.reduction_mensuelle_cents !== null
        ? String(eleve.reduction_mensuelle_cents / 100)
        : '',
    )
    setMatiereIds(inscriptionsActives.map((i) => i.matiere_id))
    setPanneauOuvert(true)
  }

  const basculerMatiere = (id: number) =>
    setMatiereIds((actuel) =>
      actuel.includes(id) ? actuel.filter((m) => m !== id) : [...actuel, id],
    )

  const soumettreEngagement = () => {
    setErreur(null)
    let reduction_mensuelle_cents: number | null = null
    if (reductionActive) {
      try {
        reduction_mensuelle_cents = dirhamsVersCentimes(reductionDh)
      } catch {
        setErreur('Montant de réduction invalide.')
        return
      }
    }
    modifierEngagement.mutate(
      {
        id: eleve.id,
        periode_application: periodeApplication,
        est_pack: estPack,
        reduction_mensuelle_cents,
        matiere_ids: estPack ? [] : matiereIds,
      },
      { onSuccess: () => setPanneauOuvert(false), onError: gererErreur },
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-medium">
            {eleve.prenom} {eleve.nom}
          </h1>
          <p className="font-mono text-xs text-muted-foreground">{eleve.matricule}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border px-2 py-1 text-xs">{eleve.statut}</span>
          <Button asChild size="sm">
            <Link to={`/caisse/${eleve.id}`}>Caisse</Link>
          </Button>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div className="text-muted-foreground">Niveau</div>
        <div>{eleve.niveau_code}</div>
        <div className="text-muted-foreground">Téléphone parent</div>
        <div>{eleve.telephone_parent}</div>
        {eleve.telephone_eleve && (
          <>
            <div className="text-muted-foreground">Téléphone élève</div>
            <div>{eleve.telephone_eleve}</div>
          </>
        )}
        <div className="text-muted-foreground">Date d'inscription</div>
        <div>{eleve.date_inscription}</div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-medium">Matières inscrites</h2>
          {eleve.est_pack && <Badge variant="secondary">Pack</Badge>}
          {eleve.reduction_mensuelle_cents !== null && (
            <Badge variant="secondary">
              Réduction ({formaterMontant(eleve.reduction_mensuelle_cents)}/mois)
            </Badge>
          )}
        </div>
        <table className="w-full text-sm">
          <tbody>
            {inscriptionsActives.map((inscription) => (
              <tr key={inscription.id} className="border-b">
                <td className="py-1">{nomMatiere(inscription.matiere_id)}</td>
                <td className="py-1 text-right">
                  {formaterMontant(inscription.tarif_mensuel_cents)} / mois
                </td>
              </tr>
            ))}
            <tr className="font-medium">
              <td className="py-1">
                Total mensuel
                {eleve.reduction_mensuelle_cents !== null && (
                  <span className="ml-1 font-normal text-muted-foreground">(réduction)</span>
                )}
              </td>
              <td className="py-1 text-right">{formaterMontant(totalMensuel)}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="space-y-3 rounded-lg border p-3 text-sm">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Matières, pack et réduction</h2>
          {!panneauOuvert && (
            <Button size="sm" variant="outline" onClick={ouvrirPanneau}>
              Modifier
            </Button>
          )}
        </div>
        {erreur && <p className="text-xs text-destructive">{erreur}</p>}

        {panneauOuvert && (
          <div className="space-y-3 border-t pt-3">
            <div className="space-y-1">
              <label htmlFor="periode_application" className="text-xs text-muted-foreground">
                Mois d'application des changements
              </label>
              <Input
                id="periode_application"
                type="month"
                value={periodeApplication}
                onChange={(e) => setPeriodeApplication(e.target.value)}
                className="h-8 w-40"
              />
            </div>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={estPack}
                onChange={() => {
                  setEstPack((v) => !v)
                  if (!estPack) setReductionActive(false)
                }}
              />
              Pack — toutes les matières du niveau
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={reductionActive}
                onChange={() => {
                  setReductionActive((v) => !v)
                  if (!reductionActive) setEstPack(false)
                }}
              />
              Réduction — montant mensuel personnalisé
            </label>
            {reductionActive && (
              <Input
                value={reductionDh}
                onChange={(e) => setReductionDh(e.target.value)}
                placeholder="Montant (DH)"
                inputMode="decimal"
                className="h-8 w-32"
              />
            )}

            {!estPack && (
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Matières suivies</p>
                {matieresActives.map((matiere) => (
                  <label key={matiere.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={matiereIds.includes(matiere.id)}
                      onChange={() => basculerMatiere(matiere.id)}
                    />
                    {matiere.libelle}
                  </label>
                ))}
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <Button
                size="sm"
                disabled={modifierEngagement.isPending}
                onClick={soumettreEngagement}
              >
                Enregistrer
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setPanneauOuvert(false)}>
                Annuler
              </Button>
            </div>
          </div>
        )}
      </section>

      <section className="space-y-1 text-sm">
        <h2 className="font-medium">Frais d'inscription</h2>
        <p>
          {formaterMontant(eleve.frais_inscription.montant_cents)} —{' '}
          {eleve.frais_inscription.statut === 'PAYE' ? (
            <span className="text-primary">payés</span>
          ) : (
            <span className="text-destructive">impayés</span>
          )}
        </p>
      </section>

      {prochainStatut && (
        <Button
          variant="outline"
          disabled={changerStatut.isPending}
          onClick={() => changerStatut.mutate({ id: eleve.id, statut: prochainStatut })}
        >
          {prochainStatut === 'SUSPENDU' ? 'Suspendre' : 'Réactiver'}
        </Button>
      )}
    </div>
  )
}
