export interface IndicateurNiveauEleves {
  niveau_code: string
  nombre: number
}

export interface IndicateursRestreints {
  periode: string
  nombre_eleves_total: number
  nombre_eleves_par_niveau: IndicateurNiveauEleves[]
  montant_total_encaisse_cents: number
  montant_frais_inscription_cumules_cents: number
  montant_impayes_cents: number
  nombre_professeurs: number
}

export interface IndicateursComplets extends IndicateursRestreints {
  total_charges_cents: number
  total_paie_cents: number
  benefice_net_cents: number
}
