import { useLocation, useNavigate } from 'react-router-dom'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin } from '@/features/auth/hooks/useLogin'

const schemaConnexion = z.object({
  email: z.string().min(1, "L'email est requis").email('Email invalide'),
  mot_de_passe: z.string().min(1, 'Le mot de passe est requis'),
})

type DonneesConnexion = z.infer<typeof schemaConnexion>

export function PageConnexion() {
  const navigate = useNavigate()
  const location = useLocation()
  const connexion = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<DonneesConnexion>({ resolver: zodResolver(schemaConnexion) })

  const onSubmit = handleSubmit((donnees) => {
    connexion.mutate(donnees, {
      onSuccess: () => {
        const destination = (location.state as { depuis?: string } | null)?.depuis ?? '/'
        navigate(destination, { replace: true })
      },
    })
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Connexion</CardTitle>
          <CardDescription>Centre de soutien scolaire — GEP</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" {...register('email')} />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="mot_de_passe">Mot de passe</Label>
              <Input
                id="mot_de_passe"
                type="password"
                autoComplete="current-password"
                {...register('mot_de_passe')}
              />
              {errors.mot_de_passe && (
                <p className="text-sm text-destructive">{errors.mot_de_passe.message}</p>
              )}
            </div>
            {connexion.isError && (
              <p className="text-sm text-destructive" role="alert">
                {connexion.error instanceof ErreurApi && connexion.error.statut === 401
                  ? 'Email ou mot de passe incorrect.'
                  : 'Une erreur est survenue, réessayez.'}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={connexion.isPending}>
              {connexion.isPending ? 'Connexion…' : 'Se connecter'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
