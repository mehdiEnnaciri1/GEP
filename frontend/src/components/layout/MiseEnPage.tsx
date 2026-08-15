import { NavLink, Outlet } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useLogout } from '@/features/auth/hooks/useLogout'
import { useSessionStore } from '@/stores/session'
import { cn } from '@/lib/utils'

const LIENS = [
  { vers: '/', libelle: 'Accueil' },
  { vers: '/eleves', libelle: 'Élèves' },
  { vers: '/impayes', libelle: 'Impayés' },
  { vers: '/professeurs', libelle: 'Professeurs' },
  { vers: '/affectations', libelle: 'Affectations' },
  { vers: '/paie', libelle: 'Paie' },
  { vers: '/referentiel/annees-scolaires', libelle: 'Années scolaires' },
  { vers: '/referentiel/matieres', libelle: 'Matières' },
  { vers: '/referentiel/tarifs', libelle: 'Tarifs' },
  { vers: '/referentiel/parametres', libelle: 'Paramètres' },
]

export function MiseEnPage() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const deconnexion = useLogout()

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-3 print:hidden">
        <nav className="flex items-center gap-4 text-sm">
          {LIENS.map((lien) => (
            <NavLink
              key={lien.vers}
              to={lien.vers}
              end={lien.vers === '/'}
              className={({ isActive }) =>
                cn(
                  'text-muted-foreground hover:text-foreground',
                  isActive && 'font-medium text-foreground',
                )
              }
            >
              {lien.libelle}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-3 text-sm">
          {utilisateur && (
            <span className="text-muted-foreground">
              {utilisateur.prenom} {utilisateur.nom} · {utilisateur.role}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => deconnexion.mutate()}
            disabled={deconnexion.isPending}
          >
            Se déconnecter
          </Button>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
