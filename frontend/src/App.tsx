import { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { MiseEnPage } from '@/components/layout/MiseEnPage'
import { useInitialiserSession } from '@/features/auth/hooks/useInitialiserSession'
import { PageConnexion } from '@/features/auth/pages/PageConnexion'
import { PageCharges } from '@/features/charges/pages/PageCharges'
import { PageDashboard } from '@/features/dashboard/pages/PageDashboard'
import { PageCreationEleve } from '@/features/eleves/pages/PageCreationEleve'
import { PageFicheEleve } from '@/features/eleves/pages/PageFicheEleve'
import { PageListeEleves } from '@/features/eleves/pages/PageListeEleves'
import { PageGenerationPaie } from '@/features/paie/pages/PageGenerationPaie'
import { PagePaieDetail } from '@/features/paie/pages/PagePaieDetail'
import { PageCaisse } from '@/features/paiements/pages/PageCaisse'
import { PageImpayes } from '@/features/paiements/pages/PageImpayes'
import { PageFicheProfesseur } from '@/features/professeurs/pages/PageFicheProfesseur'
import { PageListeProfesseurs } from '@/features/professeurs/pages/PageListeProfesseurs'
import { PageMatriceAffectations } from '@/features/professeurs/pages/PageMatriceAffectations'
import { PageAnneesScolaires } from '@/features/referentiel/pages/PageAnneesScolaires'
import { PageGrilleTarifs } from '@/features/referentiel/pages/PageGrilleTarifs'
import { PageMatieres } from '@/features/referentiel/pages/PageMatieres'
import { PageParametres } from '@/features/referentiel/pages/PageParametres'
import { PageRapports } from '@/features/rapports/pages/PageRapports'
import { RouteProtegee } from '@/routes/RouteProtegee'

function Racine() {
  const { pret } = useInitialiserSession()

  if (!pret) return null

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/connexion" element={<PageConnexion />} />
        <Route element={<RouteProtegee />}>
          <Route element={<MiseEnPage />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<PageDashboard />} />
            <Route path="/eleves" element={<PageListeEleves />} />
            <Route path="/eleves/nouveau" element={<PageCreationEleve />} />
            <Route path="/eleves/:id" element={<PageFicheEleve />} />
            <Route path="/caisse/:id" element={<PageCaisse />} />
            <Route path="/impayes" element={<PageImpayes />} />
            <Route path="/professeurs" element={<PageListeProfesseurs />} />
            <Route path="/professeurs/:id" element={<PageFicheProfesseur />} />
            <Route path="/affectations" element={<PageMatriceAffectations />} />
            <Route path="/paie" element={<PageGenerationPaie />} />
            <Route path="/paie/:id" element={<PagePaieDetail />} />
            <Route path="/charges" element={<PageCharges />} />
            <Route path="/referentiel/annees-scolaires" element={<PageAnneesScolaires />} />
            <Route path="/referentiel/matieres" element={<PageMatieres />} />
            <Route path="/referentiel/tarifs" element={<PageGrilleTarifs />} />
            <Route path="/referentiel/parametres" element={<PageParametres />} />
            <Route path="/rapports" element={<PageRapports />} />
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
