import { useState } from 'react'

import { Link } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useGenererEcheances, useImpayes } from '@/features/paiements/hooks/usePaiements'
import { formaterMontant } from '@/lib/money'

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

export function PageImpayes() {
  const [periode, setPeriode] = useState(periodeCourante())
  const { data: impayes, isLoading } = useImpayes(periode)
  const generer = useGenererEcheances()
  const [erreur, setErreur] = useState<string | null>(null)

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Impayés</h1>
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
                      : 'Erreur lors de la génération des échéances.',
                  ),
              })
            }}
          >
            Générer les échéances de {periode}
          </Button>
        </div>
      </div>
      {erreur && <p className="text-sm text-destructive">{erreur}</p>}
      {generer.isSuccess && (
        <p className="text-sm text-muted-foreground">
          {generer.data.nombre_generees} échéance(s) générée(s).
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : impayes?.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <img src="/vide-finances.png" alt="" className="size-32" />
          <p className="text-sm text-muted-foreground">Aucun impayé pour cette période.</p>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Élève</th>
              <th className="py-2 text-right">Dû</th>
              <th className="py-2 text-right">Payé</th>
              <th className="py-2 text-right">Reste</th>
              <th className="py-2">Statut</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {impayes?.map((echeance) => (
              <tr key={echeance.id} className="border-b">
                <td className="py-2">
                  {echeance.eleve_prenom} {echeance.eleve_nom}
                  <span className="ml-2 font-mono text-xs text-muted-foreground">
                    {echeance.eleve_matricule}
                  </span>
                </td>
                <td className="py-2 text-right">{formaterMontant(echeance.montant_du_cents)}</td>
                <td className="py-2 text-right">{formaterMontant(echeance.montant_paye_cents)}</td>
                <td className="py-2 text-right">
                  {formaterMontant(echeance.montant_du_cents - echeance.montant_paye_cents)}
                </td>
                <td className="py-2">{echeance.statut}</td>
                <td className="py-2 text-right">
                  <Link
                    to={`/caisse/${echeance.eleve_id}`}
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    Encaisser
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
