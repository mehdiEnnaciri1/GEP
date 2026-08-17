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
    <div className="flex min-h-screen bg-background">
      <div className="relative hidden flex-1 items-center justify-center overflow-hidden bg-secondary/40 lg:flex">
        <div className="pointer-events-none absolute -top-24 -left-24 size-72 rounded-full bg-chart-5/15 blur-3xl" />
        <div className="pointer-events-none absolute -right-24 -bottom-24 size-72 rounded-full bg-chart-1/15 blur-3xl" />
        <img
          src="/illustration-connexion.jpg"
          alt="Salle de classe d'un centre de soutien scolaire"
          className="relative max-h-[85vh] w-full max-w-lg rounded-2xl object-cover shadow-lg"
        />
      </div>

      <div className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <div className="mb-1 flex size-11 items-center justify-center rounded-xl bg-primary/10">
              <img src="/logo.png" alt="" className="size-7" />
            </div>
            <CardTitle className="text-lg">Connexion</CardTitle>
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
    </div>
  )
}
