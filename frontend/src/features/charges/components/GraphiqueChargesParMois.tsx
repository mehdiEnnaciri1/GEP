import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { EvolutionCharges } from '@/features/charges/types'
import { centimesVersDirhams, formaterMontant } from '@/lib/money'

// Une année scolaire va toujours de septembre à août (voir service backend) —
// l'ordre des points reçus suit déjà cette convention.
const LIBELLES_MOIS = ['Sept', 'Oct', 'Nov', 'Déc', 'Janv', 'Févr', 'Mars', 'Avr', 'Mai', 'Juin', 'Juil', 'Août']

interface LigneGraphe {
  mois: string
  montantDh: number
  montantCents: number
}

export function GraphiqueChargesParMois({
  evolution,
  isLoading,
}: {
  evolution: EvolutionCharges | undefined
  isLoading: boolean
}) {
  if (isLoading) {
    return <Skeleton className="h-64 rounded-xl" />
  }

  if (!evolution) {
    return null
  }

  const donnees: LigneGraphe[] = evolution.points.map((point, index) => ({
    mois: LIBELLES_MOIS[index] ?? String(point.mois),
    montantDh: centimesVersDirhams(point.total_cents),
    montantCents: point.total_cents,
  }))

  return (
    <Card>
      <CardContent>
        <h2 className="mb-4 text-sm font-medium">
          Charges par mois — {evolution.annee_scolaire} (DH)
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={donnees} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="mois" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(_valeur, _nom, item) => [
                formaterMontant((item.payload as LigneGraphe).montantCents),
                'Charges',
              ]}
              contentStyle={{
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border)',
                background: 'var(--popover)',
                fontSize: '0.8125rem',
              }}
            />
            <Line
              type="monotone"
              dataKey="montantDh"
              stroke="var(--chart-3)"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
