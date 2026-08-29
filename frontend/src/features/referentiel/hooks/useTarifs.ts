import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { TarifEleve, TarifProfesseur } from '@/features/referentiel/types'

export function useTarifsEleve(anneeScolaireId: number | undefined) {
  return useQuery({
    queryKey: ['referentiel', 'tarifs-eleve', anneeScolaireId],
    queryFn: () =>
      api<TarifEleve[]>(`/referentiel/tarifs-eleve?annee_scolaire_id=${anneeScolaireId}`),
    enabled: anneeScolaireId !== undefined,
  })
}

export function useDefinirTarifEleve(anneeScolaireId: number | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: { niveau_code: string; matiere_id: number; montant_cents: number }) =>
      api<TarifEleve>('/referentiel/tarifs-eleve', {
        method: 'PUT',
        body: JSON.stringify({ annee_scolaire_id: anneeScolaireId, ...donnees }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['referentiel', 'tarifs-eleve', anneeScolaireId] }),
  })
}

export function useTarifsProfesseur(anneeScolaireId: number | undefined, actif = true) {
  return useQuery({
    queryKey: ['referentiel', 'tarifs-professeur', anneeScolaireId],
    queryFn: () =>
      api<TarifProfesseur[]>(
        `/referentiel/tarifs-professeur?annee_scolaire_id=${anneeScolaireId}`,
      ),
    // Réservé à ADMIN côté serveur (voir docs/adr/2026-08-16-tarifs-prof-admin-only.md) —
    // `actif` évite d'émettre un appel voué au 403 quand l'appelant est CAISSIER.
    enabled: anneeScolaireId !== undefined && actif,
  })
}

export function useDefinirTarifProfesseur(anneeScolaireId: number | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: {
      niveau_code: string
      matiere_id: number
      montant_par_eleve_cents: number
    }) =>
      api<TarifProfesseur>('/referentiel/tarifs-professeur', {
        method: 'PUT',
        body: JSON.stringify({ annee_scolaire_id: anneeScolaireId, ...donnees }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['referentiel', 'tarifs-professeur', anneeScolaireId],
      }),
  })
}
