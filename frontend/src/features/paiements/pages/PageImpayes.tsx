import { useMemo, useState } from 'react'

import { Link } from 'react-router-dom'

import { ChevronDownIcon } from 'lucide-react'

import { ErreurApi } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useGenererEcheances, useImpayes } from '@/features/paiements/hooks/usePaiements'
import type { EcheanceImpayee } from '@/features/paiements/types'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'
import { formaterMontant } from '@/lib/money'

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

const LIBELLE_STATUT: Record<string, string> = {
  NON_PAYE: 'Non payé',
  PARTIEL: 'Partiel',
  PAYE: 'Payé',
}

const VARIANT_STATUT: Record<string, 'destructive' | 'outline' | 'secondary'> = {
  NON_PAYE: 'destructive',
  PARTIEL: 'outline',
  PAYE: 'secondary',
}

function reste(echeance: EcheanceImpayee): number {
  return echeance.montant_du_cents - echeance.montant_paye_cents
}

function GroupeNiveau({
  niveauLibelle,
  echeances,
}: {
  niveauLibelle: string
  echeances: EcheanceImpayee[]
}) {
  const [ouvert, setOuvert] = useState(true)
  const sousTotal = echeances.reduce((somme, e) => somme + reste(e), 0)

  return (
    <div className="rounded-xl border">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setOuvert((o) => !o)}
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          <ChevronDownIcon className={`size-4 transition-transform ${ouvert ? '' : '-rotate-90'}`} />
          {niveauLibelle}
          <span className="text-xs font-normal text-muted-foreground">
            ({echeances.length} élève{echeances.length > 1 ? 's' : ''})
          </span>
        </span>
        <span className="text-sm font-medium">{formaterMontant(sousTotal)} restant</span>
      </button>

      {ouvert && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-t border-b text-left text-muted-foreground">
              <th className="py-2 pr-4 pl-4">Élève</th>
              <th className="py-2 pr-4 text-right">Dû</th>
              <th className="py-2 pr-4 text-right">Payé</th>
              <th className="py-2 pr-4 text-right">Reste</th>
              <th className="py-2 pr-4">Statut</th>
              <th className="py-2 pr-4" />
            </tr>
          </thead>
          <tbody>
            {echeances.map((echeance) => (
              <tr key={echeance.id} className="border-b last:border-b-0">
                <td className="py-2 pr-4 pl-4">
                  {echeance.eleve_prenom} {echeance.eleve_nom}
                  <span className="ml-2 font-mono text-xs text-muted-foreground">
                    {echeance.eleve_matricule}
                  </span>
                </td>
                <td className="py-2 pr-4 text-right">{formaterMontant(echeance.montant_du_cents)}</td>
                <td className="py-2 pr-4 text-right">{formaterMontant(echeance.montant_paye_cents)}</td>
                <td className="py-2 pr-4 text-right">{formaterMontant(reste(echeance))}</td>
                <td className="py-2 pr-4">
                  <Badge variant={VARIANT_STATUT[echeance.statut] ?? 'outline'}>
                    {LIBELLE_STATUT[echeance.statut] ?? echeance.statut}
                  </Badge>
                </td>
                <td className="py-2 pr-4 text-right">
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

export function PageImpayes() {
  const [periode, setPeriode] = useState(periodeCourante())
  const [niveauFiltre, setNiveauFiltre] = useState<string>('TOUS')
  const { data: impayes, isLoading } = useImpayes(periode)
  const { data: niveaux } = useNiveaux()
  const generer = useGenererEcheances()
  const [erreur, setErreur] = useState<string | null>(null)

  const groupes = useMemo(() => {
    if (!impayes) return []

    const filtres =
      niveauFiltre === 'TOUS' ? impayes : impayes.filter((e) => e.eleve_niveau_code === niveauFiltre)

    const parNiveau = new Map<string, EcheanceImpayee[]>()
    for (const echeance of filtres) {
      const liste = parNiveau.get(echeance.eleve_niveau_code) ?? []
      liste.push(echeance)
      parNiveau.set(echeance.eleve_niveau_code, liste)
    }

    const ordreNiveaux = niveaux ?? []
    return ordreNiveaux
      .filter((n) => parNiveau.has(n.code))
      .map((n) => ({
        code: n.code,
        libelle: n.libelle,
        echeances: [...(parNiveau.get(n.code) ?? [])].sort((a, b) => reste(b) - reste(a)),
      }))
  }, [impayes, niveaux, niveauFiltre])

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-heading text-xl font-semibold">Impayés</h1>
        <div className="flex items-end gap-2">
          <Select value={niveauFiltre} onValueChange={setNiveauFiltre}>
            <SelectTrigger className="bg-card">
              <SelectValue placeholder="Tous les niveaux" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="TOUS">Tous les niveaux</SelectItem>
              {niveaux?.map((n) => (
                <SelectItem key={n.code} value={n.code}>
                  {n.libelle}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={periode}
            onChange={(e) => setPeriode(e.target.value)}
            className="w-28 bg-card"
          />
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
      ) : groupes.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <img src="/vide-finances.png" alt="" className="size-32" />
          <p className="text-sm text-muted-foreground">Aucun impayé pour cette période.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groupes.map((groupe) => (
            <GroupeNiveau key={groupe.code} niveauLibelle={groupe.libelle} echeances={groupe.echeances} />
          ))}
        </div>
      )}
    </div>
  )
}
