import { useState } from 'react'

import {
  useIndicateursComplets,
  useIndicateursRestreints,
} from '@/features/dashboard/hooks/useDashboard'
import type { IndicateursComplets, IndicateursRestreints } from '@/features/dashboard/types'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'
import { formaterMontant } from '@/lib/money'
import { useSessionStore } from '@/stores/session'

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

function Carte({ titre, valeur }: { titre: string; valeur: string }) {
  return (
    <div className="space-y-1 rounded-lg border p-4">
      <p className="text-xs text-muted-foreground">{titre}</p>
      <p className="text-lg font-medium">{valeur}</p>
    </div>
  )
}

function estComplet(
  indicateurs: IndicateursComplets | IndicateursRestreints | undefined,
): indicateurs is IndicateursComplets {
  return indicateurs !== undefined && 'benefice_net_cents' in indicateurs
}

export function PageDashboard() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const estAdmin = utilisateur?.role === 'ADMIN'
  const [periode, setPeriode] = useState(periodeCourante())
  const { data: niveaux } = useNiveaux()

  // Un seul des deux hooks est réellement "enabled" selon le rôle — l'autre
  // reste inactif (voir `enabled` dans les hooks), pas de double appel réseau.
  const restreint = useIndicateursRestreints(estAdmin ? undefined : periode)
  const complet = useIndicateursComplets(estAdmin ? periode : undefined)
  const indicateurs = estAdmin ? complet.data : restreint.data
  const isLoading = estAdmin ? complet.isLoading : restreint.isLoading

  const libelleNiveau = (niveauCode: string) =>
    niveaux?.find((n) => n.code === niveauCode)?.libelle ?? niveauCode

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-medium">Tableau de bord</h1>
        <input
          value={periode}
          onChange={(e) => setPeriode(e.target.value)}
          className="w-28 rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
        />
      </div>

      {isLoading || !indicateurs ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Carte titre="Élèves" valeur={String(indicateurs.nombre_eleves_total)} />
            <Carte titre="Professeurs" valeur={String(indicateurs.nombre_professeurs)} />
            <Carte
              titre="Encaissé ce mois"
              valeur={formaterMontant(indicateurs.montant_total_encaisse_cents)}
            />
            <Carte
              titre="Frais d'inscription cumulés"
              valeur={formaterMontant(indicateurs.montant_frais_inscription_cumules_cents)}
            />
            <Carte
              titre="Impayés"
              valeur={formaterMontant(indicateurs.montant_impayes_cents)}
            />
            {estComplet(indicateurs) && (
              <>
                <Carte
                  titre="Charges du mois"
                  valeur={formaterMontant(indicateurs.total_charges_cents)}
                />
                <Carte
                  titre="Paie du mois"
                  valeur={formaterMontant(indicateurs.total_paie_cents)}
                />
                <Carte
                  titre="Bénéfice net"
                  valeur={formaterMontant(indicateurs.benefice_net_cents)}
                />
              </>
            )}
          </div>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Élèves par niveau</h2>
            <table className="w-full text-sm">
              <tbody>
                {indicateurs.nombre_eleves_par_niveau.map((n) => (
                  <tr key={n.niveau_code} className="border-b">
                    <td className="py-1">{libelleNiveau(n.niveau_code)}</td>
                    <td className="py-1 text-right">{n.nombre}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}
