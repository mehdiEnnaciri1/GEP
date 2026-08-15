import { useQuery } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { Niveau } from '@/features/referentiel/types'

export function useNiveaux() {
  return useQuery({
    queryKey: ['referentiel', 'niveaux'],
    queryFn: () => api<Niveau[]>('/referentiel/niveaux'),
    staleTime: Infinity, // table figée par le cahier des charges, ne change jamais en cours de session
  })
}
