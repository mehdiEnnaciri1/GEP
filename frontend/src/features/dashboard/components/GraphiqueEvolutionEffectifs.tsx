import { useState } from 'react'

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { EvolutionAnnee } from '@/features/dashboard/types'

// Une année scolaire va toujours d'août à juillet (voir service backend) —
// l'ordre des points reçus suit déjà cette convention, seul le libellé
// affiché sur l'axe X est dérivé ici.
const LIBELLES_MOIS = ['Août', 'Sept', 'Oct', 'Nov', 'Déc', 'Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil']

const COULEURS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
]

interface LigneGraphe {
  mois: string
  [libelleAnnee: string]: string | number
}

function fusionnerParMois(annees: EvolutionAnnee[]): LigneGraphe[] {
  return LIBELLES_MOIS.map((libelleMois, index) => {
    const ligne: LigneGraphe = { mois: libelleMois }
    for (const annee of annees) {
      ligne[annee.libelle] = annee.points[index]?.nb ?? 0
    }
    return ligne
  })
}

export function GraphiqueEvolutionEffectifs({
  annees,
  isLoading,
}: {
  annees: EvolutionAnnee[] | undefined
  isLoading: boolean
}) {
  const [masquees, setMasquees] = useState<Set<string>>(new Set())

  if (isLoading) {
    return <Skeleton className="h-72 rounded-xl" />
  }

  if (!annees || annees.length === 0) {
    return null
  }

  const donnees = fusionnerParMois(annees)

  const basculer = (libelle: string) => {
    setMasquees((precedent) => {
      const suivant = new Set(precedent)
      if (suivant.has(libelle)) suivant.delete(libelle)
      else suivant.add(libelle)
      return suivant
    })
  }

  return (
    <Card>
      <CardContent>
        <h2 className="mb-4 text-sm font-medium">Élèves par mois, toutes années scolaires</h2>
        <ResponsiveContainer width="100%" height={288}>
          <LineChart data={donnees} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="mois" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border)',
                background: 'var(--popover)',
                fontSize: '0.8125rem',
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: '0.8125rem', cursor: 'pointer' }}
              onClick={(entree) => basculer(String(entree.dataKey))}
              formatter={(valeur) => (
                <span
                  style={{
                    opacity: masquees.has(String(valeur)) ? 0.4 : 1,
                    textDecoration: masquees.has(String(valeur)) ? 'line-through' : 'none',
                  }}
                >
                  {valeur}
                </span>
              )}
            />
            {annees.map((annee, index) => (
              <Line
                key={annee.libelle}
                type="monotone"
                dataKey={annee.libelle}
                stroke={COULEURS[index % COULEURS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                hide={masquees.has(annee.libelle)}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
