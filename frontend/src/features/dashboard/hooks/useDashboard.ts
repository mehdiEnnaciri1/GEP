import { useQuery } from '@tanstack/react-query'

import { api } from '@/api/client'
import type {
  EvolutionEffectifsReponse,
  IndicateursComplets,
  IndicateursRestreints,
} from '@/features/dashboard/types'
import type { AnneeScolaire } from '@/features/referentiel/types'

export function useAnneesDisponibles() {
  return useQuery({
    queryKey: ['dashboard', 'annees-dispo'],
    queryFn: () => api<AnneeScolaire[]>('/dashboard/annees-dispo'),
  })
}

export function useIndicateursRestreints(periode: string | undefined) {
  return useQuery({
    queryKey: ['dashboard', 'restreint', periode],
    queryFn: () => api<IndicateursRestreints>(`/dashboard/restreint?periode=${periode}`),
    enabled: periode !== undefined,
  })
}

export function useIndicateursComplets(periode: string | undefined) {
  return useQuery({
    queryKey: ['dashboard', 'complet', periode],
    queryFn: () => api<IndicateursComplets>(`/dashboard/complet?periode=${periode}`),
    enabled: periode !== undefined,
  })
}

export function useEvolutionEffectifs() {
  // Graphe fixe, indépendant du filtre de période mensuel du dashboard — une
  // seule requête, jamais reliée à `periode`.
  return useQuery({
    queryKey: ['dashboard', 'evolution-effectifs'],
    queryFn: () => api<EvolutionEffectifsReponse>('/dashboard/evolution-effectifs'),
  })
}
