import { useState } from 'react'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useActiverAnneeScolaire,
  useAnneesScolaires,
  useCreerAnneeScolaire,
} from '@/features/referentiel/hooks/useAnneesScolaires'

const schema = z
  .object({
    libelle: z.string().regex(/^\d{4}-\d{4}$/, 'Format attendu : AAAA-AAAA'),
    date_debut: z.string().min(1, 'Date de début requise'),
    date_fin: z.string().min(1, 'Date de fin requise'),
  })
  .refine((v) => v.date_fin > v.date_debut, {
    message: 'La date de fin doit être après la date de début',
    path: ['date_fin'],
  })

type Donnees = z.infer<typeof schema>

export function PageAnneesScolaires() {
  const { data: annees, isLoading } = useAnneesScolaires()
  const creation = useCreerAnneeScolaire()
  const activation = useActiverAnneeScolaire()
  const [erreur, setErreur] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Donnees>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit((donnees) => {
    setErreur(null)
    creation.mutate(donnees, {
      onSuccess: () => reset(),
      onError: () => setErreur("Cette année scolaire existe déjà."),
    })
  })

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <h1 className="text-lg font-medium">Années scolaires</h1>

      <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3" noValidate>
        <div className="space-y-1">
          <Label htmlFor="libelle">Libellé</Label>
          <Input id="libelle" placeholder="2025-2026" {...register('libelle')} />
          {errors.libelle && <p className="text-xs text-destructive">{errors.libelle.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor="date_debut">Début</Label>
          <Input id="date_debut" type="date" {...register('date_debut')} />
          {errors.date_debut && (
            <p className="text-xs text-destructive">{errors.date_debut.message}</p>
          )}
        </div>
        <div className="space-y-1">
          <Label htmlFor="date_fin">Fin</Label>
          <Input id="date_fin" type="date" {...register('date_fin')} />
          {errors.date_fin && <p className="text-xs text-destructive">{errors.date_fin.message}</p>}
        </div>
        <Button type="submit" disabled={creation.isPending}>
          Créer
        </Button>
      </form>
      {erreur && <p className="text-sm text-destructive">{erreur}</p>}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Libellé</th>
              <th className="py-2">Début</th>
              <th className="py-2">Fin</th>
              <th className="py-2">Statut</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {annees?.map((annee) => (
              <tr key={annee.id} className="border-b">
                <td className="py-2">{annee.libelle}</td>
                <td className="py-2">{annee.date_debut}</td>
                <td className="py-2">{annee.date_fin}</td>
                <td className="py-2">
                  {annee.est_active ? (
                    <span className="font-medium text-primary">Active</span>
                  ) : (
                    <span className="text-muted-foreground">Inactive</span>
                  )}
                </td>
                <td className="py-2 text-right">
                  {!annee.est_active && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activation.isPending}
                      onClick={() => activation.mutate(annee.id)}
                    >
                      Activer
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
