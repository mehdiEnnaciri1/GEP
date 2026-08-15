import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { PaieMensuelle, PaieMensuelleDetail } from '@/features/paie/types'

function clePaies(periode: string | undefined) {
  return ['paie', 'liste', periode]
}

export function usePaies(periode: string | undefined) {
  return useQuery({
    queryKey: clePaies(periode),
    queryFn: () => api<PaieMensuelle[]>(`/paie?periode=${periode}`),
    enabled: periode !== undefined,
  })
}

export function usePaieDetail(id: number | undefined) {
  return useQuery({
    queryKey: ['paie', 'detail', id],
    queryFn: () => api<PaieMensuelleDetail>(`/paie/${id}`),
    enabled: id !== undefined,
  })
}

export function useMesPaies() {
  return useQuery({
    queryKey: ['paie', 'mes-paies'],
    queryFn: () => api<PaieMensuelleDetail[]>('/paie/mes-paies'),
  })
}

export function useGenererPaie(periode: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (periodeAGenerer: string) =>
      api<{ nombre_generees: number }>('/paie/generer', {
        method: 'POST',
        body: JSON.stringify({ periode: periodeAGenerer }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clePaies(periode) }),
  })
}

export function useValiderPaie(periode: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (paieId: number) =>
      api<PaieMensuelle>(`/paie/${paieId}/valider`, { method: 'POST' }),
    onSuccess: (_donnees, paieId) => {
      queryClient.invalidateQueries({ queryKey: clePaies(periode) })
      queryClient.invalidateQueries({ queryKey: ['paie', 'detail', paieId] })
    },
  })
}

interface MarquagePaye {
  paieId: number
  date_paiement: string
  mode_paiement: string
}

export function useMarquerPayee(periode: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ paieId, ...donnees }: MarquagePaye) =>
      api<PaieMensuelle>(`/paie/${paieId}/marquer-payee`, {
        method: 'POST',
        body: JSON.stringify(donnees),
      }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: clePaies(periode) })
      queryClient.invalidateQueries({ queryKey: ['paie', 'detail', variables.paieId] })
    },
  })
}
