import { useMutation } from '@tanstack/react-query'

import { ErreurApi } from '@/api/client'
import { useSessionStore } from '@/stores/session'

/** Les rapports sont des fichiers binaires, pas du JSON : le client `api()`
 * ne convient pas. On récupère les octets nous-mêmes (avec le jeton Bearer,
 * qu'un simple lien <a href> ne saurait pas ajouter) puis on déclenche un
 * téléchargement navigateur via une URL `blob:` locale et un <a download>
 * temporaire — jamais de navigation directe vers /api. */
async function telecharger(chemin: string, nomFichier: string): Promise<void> {
  const accessToken = useSessionStore.getState().accessToken
  const reponse = await fetch(`/api${chemin}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    credentials: 'include',
  })
  if (!reponse.ok) {
    const corps = (await reponse.json().catch(() => ({}))) as { detail?: string }
    throw new ErreurApi(reponse.status, corps.detail ?? reponse.statusText)
  }

  const blob = await reponse.blob()
  const url = URL.createObjectURL(blob)
  const lien = document.createElement('a')
  lien.href = url
  lien.download = nomFichier
  document.body.appendChild(lien)
  lien.click()
  lien.remove()
  URL.revokeObjectURL(url)
}

export function useTelechargerRapport() {
  return useMutation({
    mutationFn: ({ chemin, nomFichier }: { chemin: string; nomFichier: string }) =>
      telecharger(chemin, nomFichier),
  })
}
