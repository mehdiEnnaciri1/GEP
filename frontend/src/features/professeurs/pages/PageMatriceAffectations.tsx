import { useState } from 'react'

import { ErreurApi } from '@/api/client'
import { MatriceAffectations } from '@/features/professeurs/components/MatriceAffectations'
import {
  useAffectations,
  useCreerAffectation,
  useProfesseurs,
  useSupprimerAffectation,
} from '@/features/professeurs/hooks/useProfesseurs'
import { useAnneesScolaires } from '@/features/referentiel/hooks/useAnneesScolaires'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'

function aujourdhui(): string {
  return new Date().toISOString().slice(0, 10)
}

export function PageMatriceAffectations() {
  const { data: annees } = useAnneesScolaires()
  const { data: niveaux } = useNiveaux()
  const { data: matieres } = useMatieres()
  const { data: professeurs } = useProfesseurs()
  const [erreur, setErreur] = useState<string | null>(null)

  const [anneeChoisieId, setAnneeChoisieId] = useState<number | undefined>(undefined)
  const anneeParDefaut = annees?.find((a) => a.est_active) ?? annees?.[0]
  const anneeSelectionneeId = anneeChoisieId ?? anneeParDefaut?.id

  const { data: affectations } = useAffectations(anneeSelectionneeId)
  const creer = useCreerAffectation(anneeSelectionneeId)
  const supprimer = useSupprimerAffectation(anneeSelectionneeId)

  const affectationsParCle = new Map(
    affectations?.map((a) => [`${a.niveau_code}:${a.matiere_id}`, a]),
  )
  const matieresActives = matieres?.filter((m) => m.actif) ?? []

  if (!annees?.length) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-muted-foreground">
          Créez d'abord une année scolaire pour affecter des professeurs.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-medium">Matrice d'affectation</h1>
        <select
          className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
          value={anneeSelectionneeId ?? ''}
          onChange={(e) => setAnneeChoisieId(Number(e.target.value))}
        >
          {annees.map((annee) => (
            <option key={annee.id} value={annee.id}>
              {annee.libelle}
              {annee.est_active ? ' (active)' : ''}
            </option>
          ))}
        </select>
      </div>

      {erreur && <p className="text-sm text-destructive">{erreur}</p>}

      {niveaux && matieresActives.length > 0 && professeurs && (
        <MatriceAffectations
          niveaux={niveaux}
          matieres={matieresActives}
          professeurs={professeurs}
          affectationsParCle={affectationsParCle}
          mutationEnCours={creer.isPending || supprimer.isPending}
          onAssigner={(niveauCode, matiereId, professeurId) => {
            setErreur(null)
            creer.mutate(
              {
                professeur_id: professeurId,
                matiere_id: matiereId,
                niveau_code: niveauCode,
                date_debut: aujourdhui(),
              },
              {
                onError: (err) =>
                  setErreur(
                    err instanceof ErreurApi ? err.message : "Erreur lors de l'affectation.",
                  ),
              },
            )
          }}
          onRetirer={(affectationId) => {
            setErreur(null)
            supprimer.mutate(affectationId, {
              onError: (err) =>
                setErreur(err instanceof ErreurApi ? err.message : 'Erreur lors du retrait.'),
            })
          }}
        />
      )}
    </div>
  )
}
