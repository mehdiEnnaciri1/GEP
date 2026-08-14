export type RoleUtilisateur = 'ADMIN' | 'CAISSIER' | 'PROFESSEUR'

export interface UtilisateurPublic {
  id: number
  nom: string
  prenom: string
  email: string
  role: RoleUtilisateur
  actif: boolean
}

export interface LoginReponse {
  access_token: string
  token_type: string
  utilisateur: UtilisateurPublic
}

export interface AccessTokenReponse {
  access_token: string
  token_type: string
}
