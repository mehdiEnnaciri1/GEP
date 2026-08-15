import { useState } from 'react'

import { Input } from '@/components/ui/input'
import type { Matiere, Niveau } from '@/features/referentiel/types'
import { centimesVersDirhams, dirhamsVersCentimes } from '@/lib/money'

interface CelluleGrilleTarifsProps {
  valeurInitialeCents: number | undefined
  onEnregistrer: (montantCents: number) => void
  enregistrementEnCours: boolean
}

function CelluleGrilleTarifs({
  valeurInitialeCents,
  onEnregistrer,
  enregistrementEnCours,
}: CelluleGrilleTarifsProps) {
  const texteInitial =
    valeurInitialeCents !== undefined ? centimesVersDirhams(valeurInitialeCents).toString() : ''
  const [brouillon, setBrouillon] = useState(texteInitial)
  const [erreur, setErreur] = useState(false)

  const enregistrerSiModifie = () => {
    if (brouillon === texteInitial) return
    if (brouillon.trim() === '') return

    try {
      onEnregistrer(dirhamsVersCentimes(brouillon))
      setErreur(false)
    } catch {
      setErreur(true)
    }
  }

  return (
    <Input
      value={brouillon}
      onChange={(e) => setBrouillon(e.target.value)}
      onBlur={enregistrerSiModifie}
      disabled={enregistrementEnCours}
      inputMode="decimal"
      placeholder="—"
      aria-invalid={erreur}
      className="h-7 w-20 text-right"
    />
  )
}

interface GrilleTarifsProps {
  niveaux: Niveau[]
  matieres: Matiere[]
  /** clé : `${niveau_code}:${matiere_id}` */
  tarifsParCle: Map<string, number>
  onDefinirTarif: (niveauCode: string, matiereId: number, montantCents: number) => void
  enregistrementEnCours: boolean
}

/** Grille niveau × matière, en saisie tabulaire : chaque cellule s'enregistre
 * seule (au blur, si modifiée) — pas un formulaire par tarif. Les montants
 * affichés/saisis sont en dirhams, convertis via lib/money.ts uniquement. */
export function GrilleTarifs({
  niveaux,
  matieres,
  tarifsParCle,
  onDefinirTarif,
  enregistrementEnCours,
}: GrilleTarifsProps) {
  return (
    <div className="overflow-x-auto">
      <table className="text-sm">
        <thead>
          <tr>
            <th className="border-b p-2 text-left text-muted-foreground">Niveau \ Matière</th>
            {matieres.map((matiere) => (
              <th key={matiere.id} className="border-b p-2 text-center text-muted-foreground">
                {matiere.libelle}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {niveaux.map((niveau) => (
            <tr key={niveau.code}>
              <th className="border-b p-2 text-left font-normal text-muted-foreground">
                {niveau.libelle}
              </th>
              {matieres.map((matiere) => {
                const cle = `${niveau.code}:${matiere.id}`
                return (
                  <td key={matiere.id} className="border-b p-2 text-center">
                    <CelluleGrilleTarifs
                      valeurInitialeCents={tarifsParCle.get(cle)}
                      enregistrementEnCours={enregistrementEnCours}
                      onEnregistrer={(montantCents) =>
                        onDefinirTarif(niveau.code, matiere.id, montantCents)
                      }
                    />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
