import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useSessionStore } from '@/stores/session'

export function RouteProtegee() {
  const utilisateur = useSessionStore((s) => s.utilisateur)
  const location = useLocation()

  if (!utilisateur) {
    return <Navigate to="/connexion" state={{ depuis: location.pathname }} replace />
  }

  return <Outlet />
}
