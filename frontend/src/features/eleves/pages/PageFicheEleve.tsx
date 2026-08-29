import { Link, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useChangerStatutEleve, useEleve } from '@/features/eleves/hooks/useEleves'
import type { StatutEleve } from '@/features/eleves/types'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { formaterMontant } from '@/lib/money'

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

  if (isLoading || !eleve) {
    return <p className="p-6 text-sm text-muted-foreground">Chargement…</p>
  }

  const nomMatiere = (matiereId: number) =>
    matieres?.find((m) => m.id === matiereId)?.libelle ?? `Matière #${matiereId}`

  // PACK / PERSONNALISE : le montant dû réel est fixe (`montant_mensuel_fixe_cents`),
  // indépendant de la somme des tarifs par matière affichés ci-dessous — ceux-ci
  // restent réels (paie professeur), seul le total facturé à l'élève diffère.
  const totalMensuel =
    eleve.mode_facturation === 'NORMAL'
      ? eleve.inscriptions
          .filter((i) => i.date_fin === null)
          .reduce((somme, i) => somme + i.tarif_mensuel_cents, 0)
      : (eleve.montant_mensuel_fixe_cents ?? 0)

  const prochainStatut = PROCHAIN_STATUT[eleve.statut]

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
          {eleve.mode_facturation !== 'NORMAL' && (
            <span className="rounded-full border px-2 py-1 text-xs">
              {eleve.mode_facturation === 'PACK' ? 'Pack' : 'Réduction'}
            </span>
          )}
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
        <h2 className="text-sm font-medium">Matières inscrites</h2>
        <table className="w-full text-sm">
          <tbody>
            {eleve.inscriptions
              .filter((i) => i.date_fin === null)
              .map((inscription) => (
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
                {eleve.mode_facturation !== 'NORMAL' && (
                  <span className="ml-1 font-normal text-muted-foreground">
                    ({eleve.mode_facturation === 'PACK' ? 'forfait pack' : 'montant personnalisé'},
                    pas la somme ci-dessus)
                  </span>
                )}
              </td>
              <td className="py-1 text-right">{formaterMontant(totalMensuel)}</td>
            </tr>
          </tbody>
        </table>
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
