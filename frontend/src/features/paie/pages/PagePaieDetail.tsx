import { useState } from 'react'

import { useParams } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useMarquerPayee, usePaieDetail, useValiderPaie } from '@/features/paie/hooks/usePaie'
import type { ModePaiement } from '@/features/paiements/types'
import { useProfesseurs } from '@/features/professeurs/hooks/useProfesseurs'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'
import { formaterMontant } from '@/lib/money'

const MODES_PAIEMENT: ModePaiement[] = ['ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE']

function aujourdhui(): string {
  return new Date().toISOString().slice(0, 10)
}

export function PagePaieDetail() {
  const { id } = useParams<{ id: string }>()
  const paieId = id ? Number(id) : undefined
  const { data: paie, isLoading } = usePaieDetail(paieId)
  const { data: professeurs } = useProfesseurs()
  const { data: matieres } = useMatieres()
  const { data: niveaux } = useNiveaux()
  const valider = useValiderPaie(paie?.periode)
  const marquerPayee = useMarquerPayee(paie?.periode)
  const [erreur, setErreur] = useState<string | null>(null)
  const [datePaiement, setDatePaiement] = useState(aujourdhui())
  const [modePaiement, setModePaiement] = useState<ModePaiement>('VIREMENT')

  if (isLoading || !paie) {
    return <p className="p-6 text-sm text-muted-foreground">Chargement…</p>
  }

  const professeur = professeurs?.find((p) => p.id === paie.professeur_id)
  const nomProfesseur = professeur
    ? `${professeur.prenom} ${professeur.nom}`
    : `Professeur #${paie.professeur_id}`
  const nomMatiere = (matiereId: number) =>
    matieres?.find((m) => m.id === matiereId)?.libelle ?? `Matière #${matiereId}`
  const libelleNiveau = (niveauCode: string) =>
    niveaux?.find((n) => n.code === niveauCode)?.libelle ?? niveauCode

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6 print:max-w-full">
      <div className="flex items-start justify-between print:hidden">
        <div>
          <h1 className="text-lg font-medium">Bordereau de paie</h1>
          <p className="text-sm text-muted-foreground">
            {nomProfesseur} — {paie.periode}
          </p>
        </div>
        <span className="rounded-full border px-2 py-1 text-xs">{paie.statut}</span>
      </div>

      {/* En-tête visible uniquement à l'impression : le bordereau doit être */}
      {/* lisible seul, sans le contexte de l'application. */}
      <div className="hidden print:block">
        <h1 className="text-lg font-medium">Bordereau de paie</h1>
        <p className="text-sm">
          {nomProfesseur} — {paie.periode}
        </p>
      </div>

      {erreur && <p className="text-sm text-destructive print:hidden">{erreur}</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2">Niveau</th>
            <th className="py-2">Matière</th>
            <th className="py-2 text-right">Élèves</th>
            <th className="py-2 text-right">Tarif</th>
            <th className="py-2 text-right">Montant</th>
          </tr>
        </thead>
        <tbody>
          {paie.lignes.map((ligne) => (
            <tr key={ligne.id} className="border-b">
              <td className="py-2">{libelleNiveau(ligne.niveau_code)}</td>
              <td className="py-2">
                {nomMatiere(ligne.matiere_id)}
                {ligne.est_ajustement && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    (ajustement{ligne.motif_ajustement ? ` — ${ligne.motif_ajustement}` : ''})
                  </span>
                )}
              </td>
              <td className="py-2 text-right">{ligne.nombre_eleves}</td>
              <td className="py-2 text-right">{formaterMontant(ligne.tarif_unitaire_cents)}</td>
              <td className="py-2 text-right">{formaterMontant(ligne.montant_cents)}</td>
            </tr>
          ))}
          <tr className="font-medium">
            <td className="py-2" colSpan={4}>
              Total
            </td>
            <td className="py-2 text-right">{formaterMontant(paie.total_cents)}</td>
          </tr>
        </tbody>
      </table>

      <div className="flex flex-wrap items-center gap-3 print:hidden">
        <Button variant="outline" onClick={() => window.print()}>
          Imprimer
        </Button>

        {paie.statut === 'BROUILLON' && (
          <Button
            disabled={valider.isPending}
            onClick={() => {
              setErreur(null)
              valider.mutate(paie.id, {
                onError: (err) =>
                  setErreur(err instanceof ErreurApi ? err.message : 'Erreur lors de la validation.'),
              })
            }}
          >
            Valider
          </Button>
        )}

        {paie.statut === 'VALIDEE' && (
          <div className="flex items-end gap-2">
            <Input
              type="date"
              value={datePaiement}
              onChange={(e) => setDatePaiement(e.target.value)}
              className="w-40"
            />
            <select
              className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
              value={modePaiement}
              onChange={(e) => setModePaiement(e.target.value as ModePaiement)}
            >
              {MODES_PAIEMENT.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
            <Button
              disabled={marquerPayee.isPending}
              onClick={() => {
                setErreur(null)
                marquerPayee.mutate(
                  { paieId: paie.id, date_paiement: datePaiement, mode_paiement: modePaiement },
                  {
                    onError: (err) =>
                      setErreur(
                        err instanceof ErreurApi ? err.message : 'Erreur lors du marquage payée.',
                      ),
                  },
                )
              }}
            >
              Marquer payée
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
