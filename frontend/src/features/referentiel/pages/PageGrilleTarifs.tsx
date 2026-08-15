import { useState } from 'react'

import { useAnneesScolaires } from '@/features/referentiel/hooks/useAnneesScolaires'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'
import {
  useDefinirTarifEleve,
  useDefinirTarifProfesseur,
  useTarifsEleve,
  useTarifsProfesseur,
} from '@/features/referentiel/hooks/useTarifs'

import { GrilleTarifs } from '../components/GrilleTarifs'

export function PageGrilleTarifs() {
  const { data: annees } = useAnneesScolaires()
  const { data: niveaux } = useNiveaux()
  const { data: matieres } = useMatieres()

  // Choix explicite de l'utilisateur via le <select>, sinon dérivé du rendu :
  // l'année active, ou à défaut la première. Pas d'effet + setState pour
  // initialiser cette valeur — elle se calcule directement au rendu.
  const [anneeChoisieId, setAnneeChoisieId] = useState<number | undefined>(undefined)
  const anneeParDefaut = annees?.find((a) => a.est_active) ?? annees?.[0]
  const anneeSelectionneeId = anneeChoisieId ?? anneeParDefaut?.id

  const { data: tarifsEleve } = useTarifsEleve(anneeSelectionneeId)
  const { data: tarifsProfesseur } = useTarifsProfesseur(anneeSelectionneeId)
  const definirTarifEleve = useDefinirTarifEleve(anneeSelectionneeId)
  const definirTarifProfesseur = useDefinirTarifProfesseur(anneeSelectionneeId)

  const tarifsEleveParCle = new Map(
    tarifsEleve?.map((t) => [`${t.niveau_code}:${t.matiere_id}`, t.montant_cents]),
  )
  const tarifsProfesseurParCle = new Map(
    tarifsProfesseur?.map((t) => [`${t.niveau_code}:${t.matiere_id}`, t.montant_par_eleve_cents]),
  )

  const matieresActives = matieres?.filter((m) => m.actif) ?? []

  if (!annees?.length) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-muted-foreground">
          Créez d'abord une année scolaire pour saisir les tarifs.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-medium">Grille de tarifs</h1>
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

      {niveaux && matieresActives.length > 0 && (
        <>
          <section className="space-y-2">
            <h2 className="text-sm font-medium">Tarif élève (par mois, en DH)</h2>
            <GrilleTarifs
              niveaux={niveaux}
              matieres={matieresActives}
              tarifsParCle={tarifsEleveParCle}
              enregistrementEnCours={definirTarifEleve.isPending}
              onDefinirTarif={(niveauCode, matiereId, montantCents) =>
                definirTarifEleve.mutate({
                  niveau_code: niveauCode,
                  matiere_id: matiereId,
                  montant_cents: montantCents,
                })
              }
            />
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Tarif professeur (par élève, en DH)</h2>
            <GrilleTarifs
              niveaux={niveaux}
              matieres={matieresActives}
              tarifsParCle={tarifsProfesseurParCle}
              enregistrementEnCours={definirTarifProfesseur.isPending}
              onDefinirTarif={(niveauCode, matiereId, montantCents) =>
                definirTarifProfesseur.mutate({
                  niveau_code: niveauCode,
                  matiere_id: matiereId,
                  montant_par_eleve_cents: montantCents,
                })
              }
            />
          </section>
        </>
      )}
    </div>
  )
}
