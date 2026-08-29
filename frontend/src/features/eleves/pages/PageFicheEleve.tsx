import { useState } from 'react'

import { Link, useParams } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useChangerStatutEleve,
  useDefinirPack,
  useDefinirReduction,
  useEleve,
} from '@/features/eleves/hooks/useEleves'
import type { StatutEleve } from '@/features/eleves/types'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { dirhamsVersCentimes, formaterMontant } from '@/lib/money'

const PROCHAIN_STATUT: Record<StatutEleve, StatutEleve | null> = {
  ACTIF: 'SUSPENDU',
  SUSPENDU: 'ACTIF',
  ARCHIVE: null,
}

export function PageFicheEleve() {
  const { id } = useParams<{ id: string }>()
  const eleveId = id ? Number(id) : undefined
  const { data: eleve, isLoading } = useEleve(eleveId)
  const { data: matieres } = useMatieres()
  const changerStatut = useChangerStatutEleve()
  const definirPack = useDefinirPack()
  const definirReduction = useDefinirReduction()

  const [reductionDh, setReductionDh] = useState('')
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

  const gererErreur = (err: unknown) =>
    setErreur(err instanceof ErreurApi ? err.message : "Erreur lors de l'opération.")

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

      <section className="space-y-2 rounded-lg border p-3 text-sm">
        <h2 className="font-medium">Pack et réduction</h2>
        {erreur && <p className="text-xs text-destructive">{erreur}</p>}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={definirPack.isPending || eleve.reduction_mensuelle_cents !== null}
            onClick={() => {
              setErreur(null)
              definirPack.mutate(
                { id: eleve.id, actif: !eleve.est_pack },
                { onError: gererErreur },
              )
            }}
          >
            {eleve.est_pack ? 'Désactiver le pack' : 'Activer le pack'}
          </Button>

          {eleve.reduction_mensuelle_cents !== null ? (
            <Button
              size="sm"
              variant="outline"
              disabled={definirReduction.isPending}
              onClick={() => {
                setErreur(null)
                definirReduction.mutate(
                  { id: eleve.id, actif: false },
                  { onError: gererErreur },
                )
              }}
            >
              Désactiver la réduction
            </Button>
          ) : (
            <>
              <Input
                value={reductionDh}
                onChange={(e) => setReductionDh(e.target.value)}
                placeholder="Montant (DH)"
                inputMode="decimal"
                className="h-8 w-32"
                disabled={eleve.est_pack}
              />
              <Button
                size="sm"
                variant="outline"
                disabled={definirReduction.isPending || eleve.est_pack || !reductionDh.trim()}
                onClick={() => {
                  setErreur(null)
                  try {
                    const montant_cents = dirhamsVersCentimes(reductionDh)
                    definirReduction.mutate(
                      { id: eleve.id, actif: true, montant_cents },
                      { onSuccess: () => setReductionDh(''), onError: gererErreur },
                    )
                  } catch {
                    setErreur('Montant invalide.')
                  }
                }}
              >
                Activer la réduction
              </Button>
            </>
          )}
        </div>
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
