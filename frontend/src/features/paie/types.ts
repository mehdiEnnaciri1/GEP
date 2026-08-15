export type StatutPaie = 'BROUILLON' | 'VALIDEE' | 'PAYEE'

export interface LignePaie {
  id: number
  matiere_id: number
  niveau_code: string
  nombre_eleves: number
  tarif_unitaire_cents: number
  montant_cents: number
  est_ajustement: boolean
  motif_ajustement: string | null
}

export interface PaieMensuelle {
  id: number
  professeur_id: number
  periode: string
  total_cents: number
  statut: StatutPaie
  validee_le: string | null
  payee_le: string | null
  mode_paiement: string | null
}

export interface PaieMensuelleDetail extends PaieMensuelle {
  lignes: LignePaie[]
}
