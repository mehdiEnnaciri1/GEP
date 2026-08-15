import { useState } from 'react'

import { Link } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useGenererPaie, usePaies } from '@/features/paie/hooks/usePaie'
import { useProfesseurs } from '@/features/professeurs/hooks/useProfesseurs'
import { formaterMontant } from '@/lib/money'

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

const LIBELLE_STATUT: Record<string, string> = {
  BROUILLON: 'Brouillon',
  VALIDEE: 'Validée',
  PAYEE: 'Payée',
}

export function PageGenerationPaie() {
  const [periode, setPeriode] = useState(periodeCourante())
  const { data: paies, isLoading } = usePaies(periode)
  const { data: professeurs } = useProfesseurs()
  const generer = useGenererPaie(periode)
  const [erreur, setErreur] = useState<string | null>(null)

  const nomProfesseur = (professeurId: number) => {
    const professeur = professeurs?.find((p) => p.id === professeurId)
    return professeur ? `${professeur.prenom} ${professeur.nom}` : `Professeur #${professeurId}`
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Paie des professeurs</h1>
        <div className="flex items-end gap-2">
          <Input value={periode} onChange={(e) => setPeriode(e.target.value)} className="w-28" />
          <Button
            variant="outline"
            disabled={generer.isPending}
            onClick={() => {
              setErreur(null)
              generer.mutate(periode, {
                onError: (err) =>
                  setErreur(
                    err instanceof ErreurApi
                      ? err.message
                      : 'Erreur lors de la génération de la paie.',
                  ),
              })
            }}
          >
            Générer la paie de {periode}
          </Button>
        </div>
      </div>

      {erreur && <p className="text-sm text-destructive">{erreur}</p>}
      {generer.isSuccess && (
        <p className="text-sm text-muted-foreground">
          {generer.data.nombre_generees} paie(s) générée(s) ou mise(s) à jour.
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Professeur</th>
              <th className="py-2 text-right">Total</th>
              <th className="py-2">Statut</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {paies?.map((paie) => (
              <tr key={paie.id} className="border-b">
                <td className="py-2">{nomProfesseur(paie.professeur_id)}</td>
                <td className="py-2 text-right">{formaterMontant(paie.total_cents)}</td>
                <td className="py-2">{LIBELLE_STATUT[paie.statut]}</td>
                <td className="py-2 text-right">
                  <Link
                    to={`/paie/${paie.id}`}
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    Détail
                  </Link>
                </td>
              </tr>
            ))}
            {paies?.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-muted-foreground">
                  Aucune paie pour cette période.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
