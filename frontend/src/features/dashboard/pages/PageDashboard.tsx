import { useState } from 'react'

import {
  AlertCircleIcon,
  BanknoteIcon,
  GraduationCapIcon,
  HomeIcon,
  ReceiptIcon,
  TagsIcon,
  TrendingUpIcon,
  UsersIcon,
  WalletIcon,
  type LucideIcon,
} from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { GraphiqueEvolutionEffectifs } from '@/features/dashboard/components/GraphiqueEvolutionEffectifs'
import {
  useEvolutionEffectifs,
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

const ACCENTS = {
  bleu: 'bg-chart-4/15 text-chart-4',
  violet: 'bg-chart-5/15 text-chart-5',
  emeraude: 'bg-chart-1/15 text-chart-1',
  ambre: 'bg-chart-3/15 text-chart-3',
  rose: 'bg-chart-2/15 text-chart-2',
} as const

function CarteIndicateur({
  titre,
  valeur,
  icone: Icone,
  accent,
}: {
  titre: string
  valeur: string
  icone: LucideIcon
  accent: keyof typeof ACCENTS
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3">
        <div className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${ACCENTS[accent]}`}>
          <Icone className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs text-muted-foreground">{titre}</p>
          <p className="font-heading truncate text-xl font-semibold">{valeur}</p>
        </div>
      </CardContent>
    </Card>
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

  // Graphe fixe, indépendant de `periode` — une ligne par année scolaire.
  const evolutionEffectifs = useEvolutionEffectifs()

  const libelleNiveau = (niveauCode: string) =>
    niveaux?.find((n) => n.code === niveauCode)?.libelle ?? niveauCode

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-xl font-semibold">
            Bonjour{utilisateur ? `, ${utilisateur.prenom}` : ''}
          </h1>
          <p className="text-sm text-muted-foreground">Voici l'activité du centre pour la période sélectionnée.</p>
        </div>
        <Input
          value={periode}
          onChange={(e) => setPeriode(e.target.value)}
          className="w-32 bg-card"
        />
      </div>

      {isLoading || !indicateurs ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <CarteIndicateur
              titre="Élèves"
              valeur={String(indicateurs.nombre_eleves_total)}
              icone={GraduationCapIcon}
              accent="bleu"
            />
            <CarteIndicateur
              titre="Professeurs"
              valeur={String(indicateurs.nombre_professeurs)}
              icone={UsersIcon}
              accent="violet"
            />
            <CarteIndicateur
              titre="Encaissé ce mois"
              valeur={formaterMontant(indicateurs.montant_total_encaisse_cents)}
              icone={WalletIcon}
              accent="emeraude"
            />
            <CarteIndicateur
              titre="Frais d'inscription cumulés"
              valeur={formaterMontant(indicateurs.montant_frais_inscription_cumules_cents)}
              icone={TagsIcon}
              accent="ambre"
            />
            <CarteIndicateur
              titre="Impayés"
              valeur={formaterMontant(indicateurs.montant_impayes_cents)}
              icone={AlertCircleIcon}
              accent="rose"
            />
            {estComplet(indicateurs) && (
              <>
                <CarteIndicateur
                  titre="Charges du mois"
                  valeur={formaterMontant(indicateurs.total_charges_cents)}
                  icone={ReceiptIcon}
                  accent="ambre"
                />
                <CarteIndicateur
                  titre="Paie du mois"
                  valeur={formaterMontant(indicateurs.total_paie_cents)}
                  icone={BanknoteIcon}
                  accent="violet"
                />
                <CarteIndicateur
                  titre="Bénéfice net"
                  valeur={formaterMontant(indicateurs.benefice_net_cents)}
                  icone={TrendingUpIcon}
                  accent="emeraude"
                />
                <CarteIndicateur
                  titre="Marge hors loyer"
                  valeur={formaterMontant(indicateurs.marge_hors_loyer_cents)}
                  icone={HomeIcon}
                  accent="bleu"
                />
              </>
            )}
          </div>

          <GraphiqueEvolutionEffectifs
            annees={evolutionEffectifs.data?.annees}
            isLoading={evolutionEffectifs.isLoading}
          />

          <Card>
            <CardContent>
              <h2 className="mb-4 text-sm font-medium">Élèves par niveau</h2>
              <div className="space-y-3">
                {indicateurs.nombre_eleves_par_niveau.map((n) => {
                  const proportion =
                    indicateurs.nombre_eleves_total > 0
                      ? (n.nombre / indicateurs.nombre_eleves_total) * 100
                      : 0
                  return (
                    <div key={n.niveau_code} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span>{libelleNiveau(n.niveau_code)}</span>
                        <span className="text-muted-foreground">{n.nombre}</span>
                      </div>
                      <Progress value={proportion} className="h-2" />
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
