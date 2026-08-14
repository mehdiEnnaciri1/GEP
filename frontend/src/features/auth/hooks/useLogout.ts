import { useMutation } from '@tanstack/react-query'

import { api } from '@/api/client'
import { useSessionStore } from '@/stores/session'

export function useLogout() {
  const effacerSession = useSessionStore((s) => s.effacerSession)

  return useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    // Sur `settled` (succès ou échec) : quoi qu'il arrive côté serveur,
    // l'utilisateur ne doit plus se voir comme connecté localement.
    onSettled: () => {
      effacerSession()
    },
  })
}
