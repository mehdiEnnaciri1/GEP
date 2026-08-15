import { useState } from 'react'

import { useParams } from 'react-router-dom'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useEleve } from '@/features/eleves/hooks/useEleves'
import {
  useAnnulerPaiement,
  useEncaisserFraisInscription,
  useEncaisserMensualite,
  useHistoriquePaiements,
} from '@/features/paiements/hooks/usePaiements'
import type { ModePaiement } from '@/features/paiements/types'
import { dirhamsVersCentimes, formaterMontant } from '@/lib/money'

const MODES: ModePaiement[] = ['ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE']

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

function aujourdHui(): string {
  return new Date().toISOString().slice(0, 10)
}

export function PageCaisse() {
  const { id } = useParams<{ id: string }>()
  const eleveId = id ? Number(id) : undefined
  const { data: eleve } = useEleve(eleveId)
  const { data: historique } = useHistoriquePaiements(eleveId)

  const encaisserFrais = useEncaisserFraisInscription()
  const encaisserMensualite = useEncaisserMensualite()
  const annuler = useAnnulerPaiement()

  const [periode, setPeriode] = useState(periodeCourante())
  const [montantMensualite, setMontantMensualite] = useState('')
  const [mode, setMode] = useState<ModePaiement>('ESPECES')
  const [erreur, setErreur] = useState<string | null>(null)
  const [motifAnnulationId, setMotifAnnulationId] = useState<number | null>(null)
  const [motif, setMotif] = useState('')

  if (!eleve) return <p className="p-6 text-sm text-muted-foreground">Chargement…</p>

  const onEncaisserFrais = () => {
    setErreur(null)
    encaisserFrais.mutate(
      {
        eleve_id: eleve.id,
        montant_cents: eleve.frais_inscription.montant_cents,
        mode,
        date_paiement: aujourdHui(),
      },
      { onError: () => setErreur("Erreur lors de l'encaissement des frais d'inscription.") },
    )
  }

  const onEncaisserMensualite = () => {
    setErreur(null)
    try {
      const montantCents = dirhamsVersCentimes(montantMensualite)
      encaisserMensualite.mutate(
        { eleve_id: eleve.id, periode, montant_cents: montantCents, mode, date_paiement: aujourdHui() },
        {
          onSuccess: () => setMontantMensualite(''),
          onError: (err) =>
            setErreur(
              err instanceof ErreurApi
                ? err.message
                : "Erreur lors de l'encaissement.",
            ),
        },
      )
    } catch {
      setErreur('Montant invalide.')
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6">
      <div>
        <h1 className="text-lg font-medium">
          Caisse — {eleve.prenom} {eleve.nom}
        </h1>
        <p className="font-mono text-xs text-muted-foreground">{eleve.matricule}</p>
      </div>

      <div className="space-y-1">
        <Label>Mode de paiement</Label>
        <select
          className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
          value={mode}
          onChange={(e) => setMode(e.target.value as ModePaiement)}
        >
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <section className="space-y-2 rounded-lg border p-4">
        <h2 className="text-sm font-medium">Frais d'inscription</h2>
        <p className="text-sm">
          {formaterMontant(eleve.frais_inscription.montant_cents)} —{' '}
          {eleve.frais_inscription.statut === 'PAYE' ? 'payés' : 'impayés'}
        </p>
        {eleve.frais_inscription.statut !== 'PAYE' && (
          <Button size="sm" disabled={encaisserFrais.isPending} onClick={onEncaisserFrais}>
            Encaisser les frais d'inscription
          </Button>
        )}
      </section>

      <section className="space-y-2 rounded-lg border p-4">
        <h2 className="text-sm font-medium">Mensualité</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label htmlFor="periode">Période</Label>
            <Input
              id="periode"
              value={periode}
              onChange={(e) => setPeriode(e.target.value)}
              placeholder="2025-10"
              className="w-28"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="montant">Montant (DH)</Label>
            <Input
              id="montant"
              value={montantMensualite}
              onChange={(e) => setMontantMensualite(e.target.value)}
              inputMode="decimal"
              className="w-28"
            />
          </div>
          <Button disabled={encaisserMensualite.isPending} onClick={onEncaisserMensualite}>
            Encaisser
          </Button>
        </div>
        {erreur && (
          <p className="text-sm text-destructive" role="alert">
            {erreur}
          </p>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Historique</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Reçu</th>
              <th className="py-2">Type</th>
              <th className="py-2">Date</th>
              <th className="py-2 text-right">Montant</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {historique?.map((p) => (
              <tr key={p.id} className={`border-b ${p.annule_le ? 'opacity-50' : ''}`}>
                <td className="py-2 font-mono text-xs">{p.numero_recu}</td>
                <td className="py-2">
                  {p.type === 'MENSUALITE' ? `Mensualité ${p.periode}` : 'Inscription'}
                </td>
                <td className="py-2">{p.date_paiement}</td>
                <td className="py-2 text-right">{formaterMontant(p.montant_cents)}</td>
                <td className="py-2 text-right">
                  {p.annule_le ? (
                    <span className="text-xs text-destructive">annulé</span>
                  ) : motifAnnulationId === p.id ? (
                    <div className="flex items-center gap-1">
                      <Input
                        value={motif}
                        onChange={(e) => setMotif(e.target.value)}
                        placeholder="Motif"
                        className="h-7 w-32"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!motif || annuler.isPending}
                        onClick={() => {
                          annuler.mutate(
                            { id: p.id, motif },
                            { onSuccess: () => setMotifAnnulationId(null) },
                          )
                        }}
                      >
                        Confirmer
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setMotifAnnulationId(p.id)
                        setMotif('')
                      }}
                    >
                      Annuler
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
