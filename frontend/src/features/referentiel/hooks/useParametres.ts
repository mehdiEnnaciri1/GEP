import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { Parametre } from '@/features/referentiel/types'

const CLE = ['referentiel', 'parametres']

export function useParametres() {
  return useQuery({
    queryKey: CLE,
    queryFn: () => api<Parametre[]>('/referentiel/parametres'),
  })
}

export function useMettreAJourParametre() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ cle, valeur }: { cle: string; valeur: string }) =>
      api<Parametre>(`/referentiel/parametres/${cle}`, {
        method: 'PATCH',
        body: JSON.stringify({ valeur }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE }),
  })
}
