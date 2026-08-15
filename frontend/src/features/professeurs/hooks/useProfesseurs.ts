import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { Affectation, Professeur, ProfesseurDetail } from '@/features/professeurs/types'

const CLE_LISTE = ['professeurs', 'liste']

export function useProfesseurs() {
  return useQuery({
    queryKey: CLE_LISTE,
    queryFn: () => api<Professeur[]>('/professeurs'),
  })
}

export function useProfesseur(id: number | undefined) {
  return useQuery({
    queryKey: ['professeurs', 'detail', id],
    queryFn: () => api<ProfesseurDetail>(`/professeurs/${id}`),
    enabled: id !== undefined,
  })
}

export function useCreerProfesseur() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: { nom: string; prenom: string; telephone: string }) =>
      api<Professeur>('/professeurs', { method: 'POST', body: JSON.stringify(donnees) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_LISTE }),
  })
}

interface MiseAJourProfesseur {
  id: number
  nom?: string
  prenom?: string
  telephone?: string
  actif?: boolean
}

export function useMettreAJourProfesseur() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...donnees }: MiseAJourProfesseur) =>
      api<Professeur>(`/professeurs/${id}`, { method: 'PATCH', body: JSON.stringify(donnees) }),
    onSuccess: (_donnees, variables) => {
      queryClient.invalidateQueries({ queryKey: CLE_LISTE })
      queryClient.invalidateQueries({ queryKey: ['professeurs', 'detail', variables.id] })
    },
  })
}

function cleAffectations(anneeScolaireId: number | undefined) {
  return ['affectations', anneeScolaireId]
}

export function useAffectations(anneeScolaireId: number | undefined) {
  return useQuery({
    queryKey: cleAffectations(anneeScolaireId),
    queryFn: () => api<Affectation[]>(`/affectations?annee_scolaire_id=${anneeScolaireId}`),
    enabled: anneeScolaireId !== undefined,
  })
}

interface CreationAffectation {
  professeur_id: number
  matiere_id: number
  niveau_code: string
  date_debut: string
}

export function useCreerAffectation(anneeScolaireId: number | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: CreationAffectation) =>
      api<Affectation>('/affectations', {
        method: 'POST',
        body: JSON.stringify({ annee_scolaire_id: anneeScolaireId, ...donnees }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: cleAffectations(anneeScolaireId) }),
  })
}

export function useSupprimerAffectation(anneeScolaireId: number | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api<void>(`/affectations/${id}`, { method: 'DELETE' }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: cleAffectations(anneeScolaireId) }),
  })
}
