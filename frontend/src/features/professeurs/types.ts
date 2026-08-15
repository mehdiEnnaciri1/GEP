export interface Professeur {
  id: number
  nom: string
  prenom: string
  telephone: string
  actif: boolean
}

export interface Affectation {
  id: number
  professeur_id: number
  matiere_id: number
  niveau_code: string
  annee_scolaire_id: number
  date_debut: string
  date_fin: string | null
  nombre_eleves: number
}

export interface ProfesseurDetail extends Professeur {
  affectations: Affectation[]
}
