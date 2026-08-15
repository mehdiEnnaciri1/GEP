import { useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { MiseEnPage } from '@/components/layout/MiseEnPage'
import { useInitialiserSession } from '@/features/auth/hooks/useInitialiserSession'
import { PageConnexion } from '@/features/auth/pages/PageConnexion'
import { PageCreationEleve } from '@/features/eleves/pages/PageCreationEleve'
import { PageFicheEleve } from '@/features/eleves/pages/PageFicheEleve'
import { PageListeEleves } from '@/features/eleves/pages/PageListeEleves'
import { PageCaisse } from '@/features/paiements/pages/PageCaisse'
import { PageImpayes } from '@/features/paiements/pages/PageImpayes'
import { PageAnneesScolaires } from '@/features/referentiel/pages/PageAnneesScolaires'
import { PageGrilleTarifs } from '@/features/referentiel/pages/PageGrilleTarifs'
import { PageMatieres } from '@/features/referentiel/pages/PageMatieres'
import { PageParametres } from '@/features/referentiel/pages/PageParametres'
import { RouteProtegee } from '@/routes/RouteProtegee'
import { useSessionStore } from '@/stores/session'

function PageAccueil() {
  const utilisateur = useSessionStore((s) => s.utilisateur)

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-2">
      <p className="text-muted-foreground text-sm">GEP — Gestion des Élèves et des Paiements</p>
      {utilisateur && (
        <p className="text-sm">
          Connecté en tant que {utilisateur.prenom} {utilisateur.nom} ({utilisateur.role})
        </p>
      )}
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
          <Route element={<MiseEnPage />}>
            <Route path="/" element={<PageAccueil />} />
            <Route path="/eleves" element={<PageListeEleves />} />
            <Route path="/eleves/nouveau" element={<PageCreationEleve />} />
            <Route path="/eleves/:id" element={<PageFicheEleve />} />
            <Route path="/caisse/:id" element={<PageCaisse />} />
            <Route path="/impayes" element={<PageImpayes />} />
            <Route path="/referentiel/annees-scolaires" element={<PageAnneesScolaires />} />
            <Route path="/referentiel/matieres" element={<PageMatieres />} />
            <Route path="/referentiel/tarifs" element={<PageGrilleTarifs />} />
            <Route path="/referentiel/parametres" element={<PageParametres />} />
          </Route>
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
