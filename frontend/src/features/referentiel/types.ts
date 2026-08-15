export interface AnneeScolaire {
  id: number
  libelle: string
  date_debut: string
  date_fin: string
  est_active: boolean
}

export interface Niveau {
  code: string
  libelle: string
  ordre: number
}

export interface Matiere {
  id: number
  code: string
  libelle: string
  actif: boolean
}

export interface Parametre {
  cle: string
  valeur: string
  type_valeur: 'entier' | 'texte' | 'booleen'
  description: string | null
}

export interface TarifEleve {
  id: number
  annee_scolaire_id: number
  niveau_code: string
  matiere_id: number
  montant_cents: number
}

export interface TarifProfesseur {
  id: number
  annee_scolaire_id: number
  niveau_code: string
  matiere_id: number
  montant_par_eleve_cents: number
}
