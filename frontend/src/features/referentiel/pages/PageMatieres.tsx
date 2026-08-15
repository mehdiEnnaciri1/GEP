import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useCreerMatiere,
  useMatieres,
  useMettreAJourMatiere,
} from '@/features/referentiel/hooks/useMatieres'

const schema = z.object({
  code: z.string().min(1, 'Code requis').max(20),
  libelle: z.string().min(1, 'Libellé requis').max(80),
})

type Donnees = z.infer<typeof schema>

export function PageMatieres() {
  const { data: matieres, isLoading } = useMatieres()
  const creation = useCreerMatiere()
  const miseAJour = useMettreAJourMatiere()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Donnees>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit((donnees) => {
    creation.mutate(donnees, { onSuccess: () => reset() })
  })

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-lg font-medium">Matières</h1>

      <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3" noValidate>
        <div className="space-y-1">
          <Label htmlFor="code">Code</Label>
          <Input id="code" placeholder="MATH" {...register('code')} />
          {errors.code && <p className="text-xs text-destructive">{errors.code.message}</p>}
        </div>
        <div className="space-y-1">
          <Label htmlFor="libelle">Libellé</Label>
          <Input id="libelle" placeholder="Mathématiques" {...register('libelle')} />
          {errors.libelle && <p className="text-xs text-destructive">{errors.libelle.message}</p>}
        </div>
        <Button type="submit" disabled={creation.isPending}>
          Ajouter
        </Button>
      </form>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Code</th>
              <th className="py-2">Libellé</th>
              <th className="py-2">Statut</th>
            </tr>
          </thead>
          <tbody>
            {matieres?.map((matiere) => (
              <tr key={matiere.id} className="border-b">
                <td className="py-2">{matiere.code}</td>
                <td className="py-2">{matiere.libelle}</td>
                <td className="py-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={miseAJour.isPending}
                    onClick={() =>
                      miseAJour.mutate({ id: matiere.id, actif: !matiere.actif })
                    }
                  >
                    {matiere.actif ? 'Désactiver' : 'Activer'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
