import { useSessionStore } from '@/stores/session'

const PREFIXE = '/api'

export class ErreurApi extends Error {
  statut: number

  constructor(statut: number, message: string) {
    super(message)
    this.name = 'ErreurApi'
    this.statut = statut
  }
}

async function requeteBrute(chemin: string, options: RequestInit): Promise<Response> {
  const entetes = new Headers(options.headers)
  if (options.body !== undefined) entetes.set('Content-Type', 'application/json')

  const accessToken = useSessionStore.getState().accessToken
  if (accessToken) entetes.set('Authorization', `Bearer ${accessToken}`)

  // `credentials: include` : le cookie httpOnly du refresh token doit partir
  // avec chaque requête vers /api, même en relatif (voir CLAUDE.md, Frontend).
  return fetch(`${PREFIXE}${chemin}`, { ...options, headers: entetes, credentials: 'include' })
}

// Un seul rafraîchissement en vol à la fois, même si plusieurs requêtes
// essuient un 401 en même temps (plusieurs hooks TanStack Query en parallèle).
let rafraichissementEnCours: Promise<string | null> | null = null

async function rafraichir(): Promise<string | null> {
  const reponse = await fetch(`${PREFIXE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!reponse.ok) return null
  const donnees = (await reponse.json()) as { access_token: string }
  return donnees.access_token
}

/** Chemins qui ne doivent jamais déclencher une tentative de rafraîchissement
 * sur 401 : ce sont eux-mêmes le mécanisme d'authentification. */
const CHEMINS_SANS_RAFRAICHISSEMENT = new Set(['/auth/login', '/auth/refresh'])

export async function api<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  let reponse = await requeteBrute(chemin, options)

  if (reponse.status === 401 && !CHEMINS_SANS_RAFRAICHISSEMENT.has(chemin)) {
    rafraichissementEnCours ??= rafraichir().finally(() => {
      rafraichissementEnCours = null
    })
    const nouveauToken = await rafraichissementEnCours

    if (nouveauToken) {
      useSessionStore.getState().definirAccessToken(nouveauToken)
      reponse = await requeteBrute(chemin, options)
    }
  }

  if (reponse.status === 401) {
    // Rafraîchissement impossible (ou pas tenté) : déconnexion automatique.
    useSessionStore.getState().effacerSession()
  }

  if (!reponse.ok) {
    const corps = (await reponse.json().catch(() => ({}))) as { detail?: string }
    throw new ErreurApi(reponse.status, corps.detail ?? reponse.statusText)
  }

  if (reponse.status === 204) return undefined as T
  return (await reponse.json()) as T
}
