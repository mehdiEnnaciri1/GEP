export interface CategorieCharge {
  id: number
  libelle: string
  actif: boolean
}

export interface Charge {
  id: number
  categorie_id: number
  description: string
  montant_cents: number
  date_charge: string
  periode: string
  mode_paiement: string
  justificatif_type: string | null
  cree_le: string
  annule_le: string | null
}

export interface TotalCategorie {
  categorie_id: number
  total_cents: number
}

export interface TotauxCharges {
  periode: string
  total_cents: number
  par_categorie: TotalCategorie[]
}

export interface PointChargeMensuel {
  mois: number
  total_cents: number
}

export interface EvolutionCharges {
  annee_scolaire: string
  points: PointChargeMensuel[]
}
