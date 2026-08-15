import { useState } from 'react'

import { Link } from 'react-router-dom'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreerProfesseur, useProfesseurs } from '@/features/professeurs/hooks/useProfesseurs'

const schema = z.object({
  nom: z.string().min(1, 'Nom requis'),
  prenom: z.string().min(1, 'Prénom requis'),
  telephone: z.string().min(1, 'Téléphone requis'),
})

type Donnees = z.infer<typeof schema>

export function PageListeProfesseurs() {
  const { data: professeurs, isLoading } = useProfesseurs()
  const creation = useCreerProfesseur()
  const [formulaireOuvert, setFormulaireOuvert] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Donnees>({ resolver: zodResolver(schema) })

  const onSubmit = handleSubmit((donnees) => {
    creation.mutate(donnees, {
      onSuccess: () => {
        reset()
        setFormulaireOuvert(false)
      },
    })
  })

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Professeurs</h1>
        <Button variant="outline" onClick={() => setFormulaireOuvert((o) => !o)}>
          {formulaireOuvert ? 'Annuler' : 'Nouveau professeur'}
        </Button>
      </div>

      {formulaireOuvert && (
        <form onSubmit={onSubmit} noValidate className="space-y-3 rounded-lg border p-4">
          <div className="space-y-1">
            <Label htmlFor="nom">Nom</Label>
            <Input id="nom" {...register('nom')} />
            {errors.nom && <p className="text-xs text-destructive">{errors.nom.message}</p>}
          </div>
          <div className="space-y-1">
            <Label htmlFor="prenom">Prénom</Label>
            <Input id="prenom" {...register('prenom')} />
            {errors.prenom && (
              <p className="text-xs text-destructive">{errors.prenom.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label htmlFor="telephone">Téléphone</Label>
            <Input id="telephone" {...register('telephone')} />
            {errors.telephone && (
              <p className="text-xs text-destructive">{errors.telephone.message}</p>
            )}
          </div>
          {creation.isError && (
            <p className="text-sm text-destructive" role="alert">
              {creation.error instanceof ErreurApi
                ? creation.error.message
                : 'Une erreur est survenue.'}
            </p>
          )}
          <Button type="submit" disabled={creation.isPending}>
            Créer
          </Button>
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Nom</th>
              <th className="py-2">Téléphone</th>
              <th className="py-2">Statut</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {professeurs?.map((professeur) => (
              <tr key={professeur.id} className="border-b">
                <td className="py-2">
                  {professeur.prenom} {professeur.nom}
                </td>
                <td className="py-2">{professeur.telephone}</td>
                <td className="py-2">{professeur.actif ? 'Actif' : 'Inactif'}</td>
                <td className="py-2 text-right">
                  <Link
                    to={`/professeurs/${professeur.id}`}
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    Fiche
                  </Link>
                </td>
              </tr>
            ))}
            {professeurs?.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-muted-foreground">
                  Aucun professeur.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
