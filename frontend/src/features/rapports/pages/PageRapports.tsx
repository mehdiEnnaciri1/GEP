import { useState } from 'react'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTelechargerRapport } from '@/features/rapports/hooks/useRapports'
import { useSessionStore } from '@/stores/session'

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

interface LigneRapportProps {
  titre: string
  cheminPdf: string
  cheminExcel?: string
  nomFichierBase: string
  onTelecharger: (chemin: string, nomFichier: string) => void
  enCours: boolean
}

function LigneRapport({
  titre,
  cheminPdf,
  cheminExcel,
  nomFichierBase,
  onTelecharger,
  enCours,
}: LigneRapportProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <span className="text-sm font-medium">{titre}</span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={enCours}
          onClick={() => onTelecharger(cheminPdf, `${nomFichierBase}.pdf`)}
        >
          PDF
        </Button>
        {cheminExcel && (
          <Button
            variant="outline"
            size="sm"
            disabled={enCours}
            onClick={() => onTelecharger(cheminExcel, `${nomFichierBase}.xlsx`)}
          >
            Excel
          </Button>
        )}
      </div>
    </div>
  )
}

export function PageRapports() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const estAdmin = utilisateur?.role === 'ADMIN'
  const [periode, setPeriode] = useState(periodeCourante())
  const [paiementId, setPaiementId] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const telechargement = useTelechargerRapport()

  const telecharger = (chemin: string, nomFichier: string) => {
    setErreur(null)
    telechargement.mutate(
      { chemin, nomFichier },
      {
        onError: (err) =>
          setErreur(err instanceof ErreurApi ? err.message : 'Erreur lors du téléchargement.'),
      },
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-medium">Rapports</h1>
        <Input value={periode} onChange={(e) => setPeriode(e.target.value)} className="w-28" />
      </div>

      {erreur && <p className="text-sm text-destructive">{erreur}</p>}

      <div className="space-y-3">
        <LigneRapport
          titre="Liste des élèves"
          cheminPdf="/rapports/eleves/pdf"
          cheminExcel="/rapports/eleves/excel"
          nomFichierBase="liste-eleves"
          onTelecharger={telecharger}
          enCours={telechargement.isPending}
        />
        <LigneRapport
          titre="Paiements de la période"
          cheminPdf={`/rapports/paiements/pdf?periode=${periode}`}
          cheminExcel={`/rapports/paiements/excel?periode=${periode}`}
          nomFichierBase={`paiements-${periode}`}
          onTelecharger={telecharger}
          enCours={telechargement.isPending}
        />
        <LigneRapport
          titre="Impayés de la période"
          cheminPdf={`/rapports/impayes/pdf?periode=${periode}`}
          cheminExcel={`/rapports/impayes/excel?periode=${periode}`}
          nomFichierBase={`impayes-${periode}`}
          onTelecharger={telecharger}
          enCours={telechargement.isPending}
        />
        {estAdmin && (
          <>
            <LigneRapport
              titre="Paie des professeurs"
              cheminPdf={`/rapports/paie/pdf?periode=${periode}`}
              cheminExcel={`/rapports/paie/excel?periode=${periode}`}
              nomFichierBase={`paie-${periode}`}
              onTelecharger={telecharger}
              enCours={telechargement.isPending}
            />
            <LigneRapport
              titre="Récapitulatif mensuel"
              cheminPdf={`/rapports/recapitulatif/pdf?periode=${periode}`}
              cheminExcel={`/rapports/recapitulatif/excel?periode=${periode}`}
              nomFichierBase={`recapitulatif-${periode}`}
              onTelecharger={telecharger}
              enCours={telechargement.isPending}
            />
          </>
        )}
      </div>

      <section className="space-y-2 rounded-lg border p-4">
        <h2 className="text-sm font-medium">Reçu individuel</h2>
        <div className="flex items-end gap-2">
          <div className="space-y-1">
            <Label htmlFor="paiement-id">Identifiant du paiement</Label>
            <Input
              id="paiement-id"
              value={paiementId}
              onChange={(e) => setPaiementId(e.target.value)}
              className="w-32"
            />
          </div>
          <Button
            variant="outline"
            disabled={!paiementId.trim() || telechargement.isPending}
            onClick={() =>
              telecharger(`/rapports/recu/${paiementId}/pdf`, `recu-${paiementId}.pdf`)
            }
          >
            Télécharger le reçu
          </Button>
        </div>
      </section>
    </div>
  )
}
