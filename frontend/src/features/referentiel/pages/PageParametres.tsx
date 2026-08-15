import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useMettreAJourParametre, useParametres } from '@/features/referentiel/hooks/useParametres'

function LigneParametre({
  cle,
  valeur,
  description,
}: {
  cle: string
  valeur: string
  description: string | null
}) {
  const [brouillon, setBrouillon] = useState(valeur)
  const miseAJour = useMettreAJourParametre()

  const modifie = brouillon !== valeur

  return (
    <tr className="border-b align-top">
      <td className="py-2 pr-4">
        <div className="font-mono text-xs">{cle}</div>
        {description && <div className="text-xs text-muted-foreground">{description}</div>}
      </td>
      <td className="py-2 pr-4">
        <Input
          value={brouillon}
          onChange={(e) => setBrouillon(e.target.value)}
          className="w-40"
        />
      </td>
      <td className="py-2">
        <Button
          size="sm"
          variant="outline"
          disabled={!modifie || miseAJour.isPending}
          onClick={() => miseAJour.mutate({ cle, valeur: brouillon })}
        >
          Enregistrer
        </Button>
      </td>
    </tr>
  )
}

export function PageParametres() {
  const { data: parametres, isLoading } = useParametres()

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-lg font-medium">Paramètres</h1>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {parametres?.map((parametre) => (
              <LigneParametre
                key={parametre.cle}
                cle={parametre.cle}
                valeur={parametre.valeur}
                description={parametre.description}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
