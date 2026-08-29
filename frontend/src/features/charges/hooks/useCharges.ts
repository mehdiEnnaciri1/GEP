import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, ErreurApi } from '@/api/client'
import type {
  CategorieCharge,
  Charge,
  EvolutionCharges,
  TotauxCharges,
} from '@/features/charges/types'
import { useSessionStore } from '@/stores/session'

const CLE_CATEGORIES = ['charges', 'categories']

export function useCategoriesCharge() {
  return useQuery({
    queryKey: CLE_CATEGORIES,
    queryFn: () => api<CategorieCharge[]>('/charges/categories'),
  })
}

export function useCreerCategorieCharge() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (libelle: string) =>
      api<CategorieCharge>('/charges/categories', {
        method: 'POST',
        body: JSON.stringify({ libelle }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CLE_CATEGORIES }),
  })
}

interface FiltresCharges {
  periode?: string
  categorie_id?: number
}

function cleCharges(filtres: FiltresCharges) {
  return ['charges', 'liste', filtres]
}

function construireParametres(filtres: FiltresCharges): string {
  const params = new URLSearchParams()
  if (filtres.periode) params.set('periode', filtres.periode)
  if (filtres.categorie_id) params.set('categorie_id', String(filtres.categorie_id))
  return params.toString()
}

export function useCharges(filtres: FiltresCharges) {
  return useQuery({
    queryKey: cleCharges(filtres),
    queryFn: () => api<Charge[]>(`/charges?${construireParametres(filtres)}`),
  })
}

export function useTotauxCharges(periode: string | undefined) {
  return useQuery({
    queryKey: ['charges', 'totaux', periode],
    queryFn: () => api<TotauxCharges>(`/charges/totaux?periode=${periode}`),
    enabled: periode !== undefined,
  })
}

export function useEvolutionCharges() {
  // Graphe fixe, indépendant du filtre de période de la page — une seule
  // requête, jamais reliée à `periodeFiltre`.
  return useQuery({
    queryKey: ['charges', 'evolution-mensuelle'],
    queryFn: () => api<EvolutionCharges>('/charges/evolution-mensuelle'),
  })
}

export interface CreationCharge {
  categorie_id: number
  description: string
  montant_cents: number
  date_charge: string
  periode: string
  mode_paiement: string
  justificatif: File | null
}

export function useCreerCharge() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (donnees: CreationCharge) => {
      const formulaire = new FormData()
      formulaire.set('categorie_id', String(donnees.categorie_id))
      formulaire.set('description', donnees.description)
      formulaire.set('montant_cents', String(donnees.montant_cents))
      formulaire.set('date_charge', donnees.date_charge)
      formulaire.set('periode', donnees.periode)
      formulaire.set('mode_paiement', donnees.mode_paiement)
      if (donnees.justificatif) formulaire.set('justificatif', donnees.justificatif)

      return api<Charge>('/charges', { method: 'POST', body: formulaire })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['charges', 'liste'] })
      queryClient.invalidateQueries({ queryKey: ['charges', 'totaux'] })
    },
  })
}

export function useAnnulerCharge() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api<Charge>(`/charges/${id}/annuler`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['charges', 'liste'] })
      queryClient.invalidateQueries({ queryKey: ['charges', 'totaux'] })
    },
  })
}

/** Le justificatif n'est pas du JSON : le client `api()` ne convient pas.
 * Un <img src="/api/..."> ne conviendrait pas non plus — l'authentification
 * se fait par jeton Bearer en en-tête, pas par cookie, et le navigateur ne
 * sait pas ajouter cet en-tête à une requête d'image. On récupère donc les
 * octets nous-mêmes et on en fait une URL `blob:` locale. */
export function useJustificatif(chargeId: number | undefined) {
  return useQuery({
    queryKey: ['charges', 'justificatif', chargeId],
    queryFn: async () => {
      const accessToken = useSessionStore.getState().accessToken
      const reponse = await fetch(`/api/charges/${chargeId}/justificatif`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        credentials: 'include',
      })
      if (!reponse.ok) throw new ErreurApi(reponse.status, reponse.statusText)
      const blob = await reponse.blob()
      return { url: URL.createObjectURL(blob), type: blob.type }
    },
    enabled: chargeId !== undefined,
    staleTime: Infinity,
  })
}
