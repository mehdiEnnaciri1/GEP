import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { AnneeScolaire } from '@/features/referentiel/types'

const CLE = ['referentiel', 'annees-scolaires']

export function useAnneesScolaires() {
  return useQuery({
    queryKey: CLE,
    queryFn: () => api<AnneeScolaire[]>('/referentiel/annees-scolaires'),
  })
}

interface CreationAnnee {
  libelle: string
  date_debut: string
  date_fin: string
}

export function useCreerAnneeScolaire() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: CreationAnnee) =>
      api<AnneeScolaire>('/referentiel/annees-scolaires', {
        method: 'POST',
        body: JSON.stringify(donnees),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE }),
  })
}

export function useActiverAnneeScolaire() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      api<AnneeScolaire>(`/referentiel/annees-scolaires/${id}/activer`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE }),
  })
}
