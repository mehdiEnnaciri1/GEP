import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { useSessionStore } from './stores/session'

const ETAT_INITIAL_SESSION = useSessionStore.getInitialState()

function reponse(corps: unknown, ok: boolean) {
  return {
    ok,
    status: ok ? 200 : 401,
    json: async () => corps,
  } as Response
}

describe('App', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    // Le store de session est un singleton module-level : sans ça, l'état
    // (pret, utilisateur) fuite d'un test à l'autre.
    useSessionStore.setState(ETAT_INITIAL_SESSION, true)
    // jsdom conserve son `window.history` d'un test à l'autre dans le même
    // fichier : sans ça, la redirection vers /connexion d'un test précédent
    // reste l'URL courante du test suivant.
    window.history.pushState({}, '', '/')
  })

  it('redirige vers la page de connexion sans session valide', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(reponse({ detail: 'Authentification requise.' }, false)),
    )

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Connexion')).toBeInTheDocument()
    })
  })

  it('affiche la page protégée avec une session valide', async () => {
    const utilisateur = {
      id: 1,
      nom: 'Admin',
      prenom: 'Test',
      email: 'admin@test.ma',
      role: 'ADMIN',
      actif: true,
    }

    const fetchMock = vi.fn((entree: RequestInfo | URL) => {
      const url = String(entree)
      if (url.includes('/auth/refresh')) return Promise.resolve(reponse({ access_token: 'x' }, true))
      if (url.includes('/auth/me')) return Promise.resolve(reponse(utilisateur, true))
      return Promise.resolve(reponse({}, false))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText(/Connecté en tant que Test Admin/)).toBeInTheDocument()
    })
  })
})
