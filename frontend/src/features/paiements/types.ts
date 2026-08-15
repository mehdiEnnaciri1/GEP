export type ModePaiement = 'ESPECES' | 'VIREMENT' | 'CHEQUE' | 'CARTE' | 'AUTRE'
export type TypePaiement = 'MENSUALITE' | 'INSCRIPTION'
export type StatutEcheance = 'NON_PAYE' | 'PARTIEL' | 'PAYE'

export interface Paiement {
  id: number
  numero_recu: string
  eleve_id: number
  type: TypePaiement
  periode: string | null
  montant_cents: number
  date_paiement: string
  mode: ModePaiement
  observation: string | null
  annule_le: string | null
  motif_annulation: string | null
}

export interface Echeance {
  id: number
  eleve_id: number
  periode: string
  montant_du_cents: number
  montant_paye_cents: number
  statut: StatutEcheance
}

export interface EcheanceImpayee extends Echeance {
  eleve_nom: string
  eleve_prenom: string
  eleve_matricule: string
}
