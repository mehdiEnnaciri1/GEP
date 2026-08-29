import { useState } from 'react'

import { Input } from '@/components/ui/input'
import type { Niveau } from '@/features/referentiel/types'
import { centimesVersDirhams, dirhamsVersCentimes } from '@/lib/money'

interface CellulePackProps {
  valeurInitialeCents: number | undefined
  onEnregistrer: (montantCents: number) => void
  enregistrementEnCours: boolean
}

function CellulePack({ valeurInitialeCents, onEnregistrer, enregistrementEnCours }: CellulePackProps) {
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
      className="h-7 w-24 text-right"
    />
  )
}

interface GrillePackProps {
  niveaux: Niveau[]
  /** clé : niveau_code */
  tarifsParCle: Map<string, number>
  onDefinirTarif: (niveauCode: string, montantCents: number) => void
  enregistrementEnCours: boolean
}

/** Un forfait par niveau, toutes matières tarifées confondues — contrairement
 * à `GrilleTarifs`, une seule colonne, pas de croisement avec les matières. */
export function GrillePack({
  niveaux,
  tarifsParCle,
  onDefinirTarif,
  enregistrementEnCours,
}: GrillePackProps) {
  return (
    <div className="overflow-x-auto">
      <table className="text-sm">
        <thead>
          <tr>
            <th className="border-b p-2 text-left text-muted-foreground">Niveau</th>
            <th className="border-b p-2 text-center text-muted-foreground">Forfait pack</th>
          </tr>
        </thead>
        <tbody>
          {niveaux.map((niveau) => (
            <tr key={niveau.code}>
              <th className="border-b p-2 text-left font-normal text-muted-foreground">
                {niveau.libelle}
              </th>
              <td className="border-b p-2 text-center">
                <CellulePack
                  valeurInitialeCents={tarifsParCle.get(niveau.code)}
                  enregistrementEnCours={enregistrementEnCours}
                  onEnregistrer={(montantCents) => onDefinirTarif(niveau.code, montantCents)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
