import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { CategorieCharge, TotauxCharges } from '@/features/charges/types'
import { centimesVersDirhams, formaterMontant } from '@/lib/money'

const COULEURS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
]

interface BarreDonnees {
  categorie: string
  montantDh: number
  montantCents: number
}

export function GraphiqueChargesParCategorie({
  totaux,
  categories,
  periode,
  isLoading,
}: {
  totaux: TotauxCharges | undefined
  categories: CategorieCharge[] | undefined
  periode: string
  isLoading: boolean
}) {
  if (isLoading) {
    return <Skeleton className="h-64 rounded-xl" />
  }

  if (!totaux || totaux.par_categorie.length === 0) {
    return null
  }

  const nomCategorie = (categorieId: number) =>
    categories?.find((c) => c.id === categorieId)?.libelle ?? `Catégorie #${categorieId}`

  const donnees: BarreDonnees[] = [...totaux.par_categorie]
    .sort((a, b) => b.total_cents - a.total_cents)
    .map((c) => ({
      categorie: nomCategorie(c.categorie_id),
      montantDh: centimesVersDirhams(c.total_cents),
      montantCents: c.total_cents,
    }))

  return (
    <Card>
      <CardContent>
        <h2 className="mb-4 text-sm font-medium">Charges par catégorie — {periode} (DH)</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={donnees} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
            <XAxis dataKey="categorie" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
              label={{ value: 'DH', position: 'insideTopLeft', fontSize: 12 }}
            />
            <Tooltip
              formatter={(_valeur, _nom, item) => [
                formaterMontant((item.payload as BarreDonnees).montantCents),
                'Montant',
              ]}
              contentStyle={{
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border)',
                background: 'var(--popover)',
                fontSize: '0.8125rem',
              }}
            />
            <Bar dataKey="montantDh" radius={[6, 6, 0, 0]}>
              {donnees.map((_entree, index) => (
                <Cell key={index} fill={COULEURS[index % COULEURS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
