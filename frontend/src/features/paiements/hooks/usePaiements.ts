import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { EcheanceImpayee, ModePaiement, Paiement } from '@/features/paiements/types'

function cleEleve(eleveId: number) {
  return ['eleves', 'detail', eleveId]
}

export function useHistoriquePaiements(eleveId: number | undefined) {
  return useQuery({
    queryKey: ['paiements', 'historique', eleveId],
    queryFn: () => api<Paiement[]>(`/paiements/historique/${eleveId}`),
    enabled: eleveId !== undefined,
  })
}

export function useImpayes(periode: string) {
  return useQuery({
    queryKey: ['paiements', 'impayes', periode],
    queryFn: () => api<EcheanceImpayee[]>(`/paiements/impayes?periode=${periode}`),
  })
}

interface EncaissementFraisInscription {
  eleve_id: number
  montant_cents: number
  mode: ModePaiement
  date_paiement: string
}

export function useEncaisserFraisInscription() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: EncaissementFraisInscription) =>
      api<Paiement>('/paiements/frais-inscription', {
        method: 'POST',
        body: JSON.stringify(donnees),
      }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: cleEleve(variables.eleve_id) })
      queryClient.invalidateQueries({ queryKey: ['paiements', 'historique', variables.eleve_id] })
    },
  })
}

interface EncaissementMensualite {
  eleve_id: number
  periode: string
  montant_cents: number
  mode: ModePaiement
  date_paiement: string
}

export function useEncaisserMensualite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: EncaissementMensualite) =>
      api<Paiement>('/paiements/mensualite', { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: ['paiements', 'impayes'] })
      queryClient.invalidateQueries({ queryKey: ['paiements', 'historique', variables.eleve_id] })
    },
  })
}

export function useAnnulerPaiement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motif }: { id: number; motif: string }) =>
      api<Paiement>(`/paiements/${id}/annuler`, {
        method: 'POST',
        body: JSON.stringify({ motif }),
      }),
    onSuccess: (paiement) => {
      queryClient.invalidateQueries({ queryKey: ['paiements'] })
      queryClient.invalidateQueries({ queryKey: cleEleve(paiement.eleve_id) })
    },
  })
}

export function useGenererEcheances() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (periode: string) =>
      api<{ nombre_generees: number }>('/paiements/generer-echeances', {
        method: 'POST',
        body: JSON.stringify({ periode }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['paiements', 'impayes'] }),
  })
}
