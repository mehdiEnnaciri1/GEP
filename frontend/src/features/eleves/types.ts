export type StatutEleve = 'ACTIF' | 'SUSPENDU' | 'ARCHIVE'
export type StatutFrais = 'NON_PAYE' | 'PAYE'
export type ModeFacturation = 'NORMAL' | 'PACK' | 'PERSONNALISE'

export interface InscriptionMatiere {
  id: number
  matiere_id: number
  tarif_mensuel_cents: number
  date_debut: string
  date_fin: string | null
}

export interface FraisInscription {
  id: number
  montant_cents: number
  statut: StatutFrais
  date_paiement: string | null
  mode_paiement: string | null
}

export interface Eleve {
  id: number
  matricule: string
  nom: string
  prenom: string
  telephone_eleve: string | null
  telephone_parent: string
  niveau_code: string
  annee_scolaire_id: number
  date_inscription: string
  statut: StatutEleve
  mode_facturation: ModeFacturation
  montant_mensuel_fixe_cents: number | null
  observation: string | null
}

export interface EleveDetail extends Eleve {
  inscriptions: InscriptionMatiere[]
  frais_inscription: FraisInscription
}

export interface PageEleves {
  elements: Eleve[]
  total: number
  page: number
  taille: number
}

export interface CreationEleve {
  nom: string
  prenom: string
  telephone_eleve?: string
  telephone_parent: string
  niveau_code: string
  date_inscription: string
  observation?: string
  mode_facturation?: ModeFacturation
  montant_personnalise_cents?: number
  matiere_ids: number[]
}
