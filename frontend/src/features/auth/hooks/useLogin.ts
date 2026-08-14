import { useMutation } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { LoginReponse } from '@/features/auth/types'
import { useSessionStore } from '@/stores/session'

interface Identifiants {
  email: string
  mot_de_passe: string
}

export function useLogin() {
  const definirSession = useSessionStore((s) => s.definirSession)

  return useMutation({
    mutationFn: (identifiants: Identifiants) =>
      api<LoginReponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(identifiants),
      }),
    onSuccess: (donnees) => {
      definirSession(donnees.access_token, donnees.utilisateur)
    },
  })
}
