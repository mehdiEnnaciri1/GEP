import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { Matiere } from '@/features/referentiel/types'

const CLE = ['referentiel', 'matieres']

export function useMatieres() {
  return useQuery({
    queryKey: CLE,
    queryFn: () => api<Matiere[]>('/referentiel/matieres'),
  })
}

export function useCreerMatiere() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: { code: string; libelle: string }) =>
      api<Matiere>('/referentiel/matieres', { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE }),
  })
}

export function useMettreAJourMatiere() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...donnees }: { id: number; libelle?: string; actif?: boolean }) =>
      api<Matiere>(`/referentiel/matieres/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(donnees),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE }),
  })
}
