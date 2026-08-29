import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type {
  CreationEleve,
  DefinirPackRequete,
  DefinirReductionRequete,
  Eleve,
  EleveDetail,
  PageEleves,
  StatutEleve,
} from '@/features/eleves/types'

interface FiltresEleves {
  recherche?: string
  niveau_code?: string
  statut?: StatutEleve
  page?: number
  taille?: number
}

const CLE_LISTE = ['eleves', 'liste']

function construireParametres(filtres: FiltresEleves): string {
  const params = new URLSearchParams()
  if (filtres.recherche) params.set('recherche', filtres.recherche)
  if (filtres.niveau_code) params.set('niveau_code', filtres.niveau_code)
  if (filtres.statut) params.set('statut', filtres.statut)
  params.set('page', String(filtres.page ?? 1))
  params.set('taille', String(filtres.taille ?? 20))
  return params.toString()
}

export function useEleves(filtres: FiltresEleves) {
  return useQuery({
    queryKey: [...CLE_LISTE, filtres],
    queryFn: () => api<PageEleves>(`/eleves?${construireParametres(filtres)}`),
  })
}

export function useEleve(id: number | undefined) {
  return useQuery({
    queryKey: ['eleves', 'detail', id],
    queryFn: () => api<EleveDetail>(`/eleves/${id}`),
    enabled: id !== undefined,
  })
}

export function useCreerEleve() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: CreationEleve) =>
      api<EleveDetail>('/eleves', { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_LISTE }),
  })
}

export function useChangerStatutEleve() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, statut }: { id: number; statut: StatutEleve }) =>
      api<Eleve>(`/eleves/${id}/statut`, { method: 'POST', body: JSON.stringify({ statut }) }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: CLE_LISTE })
      queryClient.invalidateQueries({ queryKey: ['eleves', 'detail', variables.id] })
    },
  })
}

export function useDefinirPack() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...donnees }: { id: number } & DefinirPackRequete) =>
      api<EleveDetail>(`/eleves/${id}/pack`, { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: CLE_LISTE })
      queryClient.invalidateQueries({ queryKey: ['eleves', 'detail', variables.id] })
    },
  })
}

export function useDefinirReduction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...donnees }: { id: number } & DefinirReductionRequete) =>
      api<Eleve>(`/eleves/${id}/reduction`, { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: CLE_LISTE })
      queryClient.invalidateQueries({ queryKey: ['eleves', 'detail', variables.id] })
    },
  })
}
