import { create } from 'zustand'

import type { UtilisateurPublic } from '@/features/auth/types'

interface EtatSession {
  accessToken: string | null
  utilisateur: UtilisateurPublic | null
  /** true dès que la tentative de reprise de session au démarrage est terminée
   * (succès ou échec) — évite de rediriger vers /connexion avant de savoir. */
  pret: boolean
  definirSession: (accessToken: string, utilisateur: UtilisateurPublic) => void
  definirAccessToken: (accessToken: string) => void
  effacerSession: () => void
  marquerPret: () => void
}

export const useSessionStore = create<EtatSession>((set) => ({
  accessToken: null,
  utilisateur: null,
  pret: false,
  definirSession: (accessToken, utilisateur) => set({ accessToken, utilisateur }),
  definirAccessToken: (accessToken) => set({ accessToken }),
  effacerSession: () => set({ accessToken: null, utilisateur: null }),
  marquerPret: () => set({ pret: true }),
}))
