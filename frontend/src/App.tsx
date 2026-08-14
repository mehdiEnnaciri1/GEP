import { useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { useInitialiserSession } from '@/features/auth/hooks/useInitialiserSession'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { PageConnexion } from '@/features/auth/pages/PageConnexion'
import { RouteProtegee } from '@/routes/RouteProtegee'
import { useSessionStore } from '@/stores/session'

function PageAccueil() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const deconnexion = useLogout()

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <p className="text-muted-foreground text-sm">GEP — Gestion des Élèves et des Paiements</p>
      {utilisateur && (
        <p className="text-sm">
          Connecté en tant que {utilisateur.prenom} {utilisateur.nom} ({utilisateur.role})
        </p>
      )}
      <Button variant="outline" onClick={() => deconnexion.mutate()} disabled={deconnexion.isPending}>
        Se déconnecter
      </Button>
    </div>
  )
}

function Racine() {
  const { pret } = useInitialiserSession()

  if (!pret) return null

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/connexion" element={<PageConnexion />} />
        <Route element={<RouteProtegee />}>
          <Route path="/" element={<PageAccueil />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

function App() {
  const [clientRequetes] = useState(() => new QueryClient())

  return (
    <QueryClientProvider client={clientRequetes}>
      <Racine />
    </QueryClientProvider>
  )
}

export default App
