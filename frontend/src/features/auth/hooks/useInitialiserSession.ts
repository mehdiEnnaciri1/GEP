import { useEffect } from 'react'

import { useQuery } from '@tanstack/react-query'

import type { UtilisateurPublic } from '@/features/auth/types'
import { useSessionStore } from '@/stores/session'

interface SessionReprise {
  accessToken: string
  utilisateur: UtilisateurPublic
}

/** Appelée une fois au démarrage de l'app : tente de reconstituer la session à
 * partir du cookie httpOnly du refresh token (`/auth/refresh`), sans quoi une
 * simple actualisation de page déconnecterait l'utilisateur. Ni l'un ni
 * l'autre appel ne passe par `api()` : il n'y a pas encore d'access token, et
 * un 401 ici ne doit surtout pas déclencher sa propre logique de
 * rafraîchissement. */
async function reprendreSession(): Promise<SessionReprise | null> {
  const reponseRefresh = await fetch('/api/auth/refresh', {
    method: 'POST',
    credentials: 'include',
  })
  if (!reponseRefresh.ok) return null

  const { access_token: accessToken } = (await reponseRefresh.json()) as { access_token: string }

  const reponseMe = await fetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: 'include',
  })
  if (!reponseMe.ok) return null

  const utilisateur = (await reponseMe.json()) as UtilisateurPublic
  return { accessToken, utilisateur }
}

export function useInitialiserSession(): { pret: boolean } {
  const pret = useSessionStore((s) => s.pret)
  const definirSession = useSessionStore((s) => s.definirSession)
  const marquerPret = useSessionStore((s) => s.marquerPret)

  const { data, isFetched } = useQuery({
    queryKey: ['session', 'reprise'],
    queryFn: reprendreSession,
    retry: false,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (!isFetched) return
    if (data) definirSession(data.accessToken, data.utilisateur)
    marquerPret()
  }, [isFetched, data, definirSession, marquerPret])

  return { pret }
}
