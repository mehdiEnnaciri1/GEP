import type { ComponentType } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import {
  BanknoteIcon,
  BookOpenIcon,
  CalendarDaysIcon,
  ClipboardListIcon,
  FileBarChartIcon,
  GraduationCapIcon,
  LayoutDashboardIcon,
  LogOutIcon,
  ReceiptIcon,
  SettingsIcon,
  TagsIcon,
  UsersIcon,
  WalletIcon,
} from 'lucide-react'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useLogout } from '@/features/auth/hooks/useLogout'
import type { RoleUtilisateur } from '@/features/auth/types'
import { useSessionStore } from '@/stores/session'
import { cn } from '@/lib/utils'

interface Lien {
  vers: string
  libelle: string
  icone: ComponentType<{ className?: string }>
  masquerPour?: RoleUtilisateur[]
}

interface GroupeLiens {
  titre: string
  liens: Lien[]
}

const GROUPES: GroupeLiens[] = [
  {
    titre: 'Général',
    liens: [{ vers: '/dashboard', libelle: 'Tableau de bord', icone: LayoutDashboardIcon }],
  },
  {
    titre: 'Pédagogie',
    liens: [
      { vers: '/eleves', libelle: 'Élèves', icone: GraduationCapIcon },
      { vers: '/professeurs', libelle: 'Professeurs', icone: UsersIcon },
      { vers: '/affectations', libelle: 'Affectations', icone: ClipboardListIcon },
    ],
  },
  {
    titre: 'Finances',
    liens: [
      { vers: '/impayes', libelle: 'Impayés', icone: WalletIcon },
      { vers: '/paie', libelle: 'Paie', icone: BanknoteIcon, masquerPour: ['CAISSIER'] },
      { vers: '/charges', libelle: 'Charges', icone: ReceiptIcon, masquerPour: ['CAISSIER'] },
    ],
  },
  {
    titre: 'Référentiel',
    liens: [
      { vers: '/referentiel/annees-scolaires', libelle: 'Années scolaires', icone: CalendarDaysIcon },
      { vers: '/referentiel/matieres', libelle: 'Matières', icone: BookOpenIcon },
      { vers: '/referentiel/tarifs', libelle: 'Tarifs', icone: TagsIcon },
      { vers: '/referentiel/parametres', libelle: 'Paramètres', icone: SettingsIcon },
    ],
  },
  {
    titre: 'Suivi',
    liens: [{ vers: '/rapports', libelle: 'Rapports', icone: FileBarChartIcon }],
  },
]

function initiales(prenom: string, nom: string) {
  return `${prenom.charAt(0)}${nom.charAt(0)}`.toUpperCase()
}

export function MiseEnPage() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const deconnexion = useLogout()

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10">
            <img src="/logo.png" alt="" className="size-6" />
          </div>
          <div className="min-w-0">
            <p className="font-heading truncate text-sm font-semibold text-sidebar-foreground">GEP</p>
            <p className="truncate text-xs text-muted-foreground">Centre de soutien scolaire</p>
          </div>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
          {GROUPES.map((groupe) => {
            const liens = groupe.liens.filter(
              (lien) => !utilisateur || !lien.masquerPour?.includes(utilisateur.role),
            )
            if (liens.length === 0) return null

            return (
              <div key={groupe.titre}>
                <p className="px-3 pb-1.5 text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">
                  {groupe.titre}
                </p>
                <div className="space-y-0.5">
                  {liens.map((lien) => (
                    <NavLink
                      key={lien.vers}
                      to={lien.vers}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground/80 transition-colors',
                          isActive
                            ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                            : 'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                        )
                      }
                    >
                      <lien.icone className="size-4 shrink-0" />
                      <span className="truncate">{lien.libelle}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            )
          })}
        </nav>

        {utilisateur && (
          <div className="flex items-center gap-2.5 border-t border-sidebar-border px-4 py-3.5">
            <Avatar className="size-8">
              <AvatarFallback className="bg-secondary text-xs font-medium text-secondary-foreground">
                {initiales(utilisateur.prenom, utilisateur.nom)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-sidebar-foreground">
                {utilisateur.prenom} {utilisateur.nom}
              </p>
              <Badge variant="secondary" className="mt-0.5">
                {utilisateur.role}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => deconnexion.mutate()}
              disabled={deconnexion.isPending}
              aria-label="Se déconnecter"
            >
              <LogOutIcon className="size-4" />
            </Button>
          </div>
        )}
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <main className="flex-1 p-5 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
