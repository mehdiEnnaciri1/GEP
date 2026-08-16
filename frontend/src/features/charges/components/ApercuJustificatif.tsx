import { useEffect } from 'react'

import { Button } from '@/components/ui/button'
import { useJustificatif } from '@/features/charges/hooks/useCharges'

interface ApercuJustificatifProps {
  chargeId: number
  onFermer: () => void
}

/** Panneau de recouvrement simple (pas de librairie de modale dans ce
 * projet) : l'URL `blob:` créée par useJustificatif est révoquée à la
 * fermeture pour ne pas fuiter de mémoire. */
export function ApercuJustificatif({ chargeId, onFermer }: ApercuJustificatifProps) {
  const { data, isLoading, isError } = useJustificatif(chargeId)

  useEffect(() => {
    return () => {
      if (data) URL.revokeObjectURL(data.url)
    }
  }, [data])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6">
      <div className="max-h-full w-full max-w-2xl space-y-3 rounded-lg bg-background p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium">Justificatif</h2>
          <Button variant="outline" size="sm" onClick={onFermer}>
            Fermer
          </Button>
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
        {isError && <p className="text-sm text-destructive">Impossible de charger le fichier.</p>}

        {data && data.type === "application/pdf" ? (
          <embed src={data.url} type="application/pdf" className="h-[70vh] w-full" />
        ) : (
          data && (
            <img src={data.url} alt="Justificatif de la charge" className="max-h-[70vh] w-full object-contain" />
          )
        )}
      </div>
    </div>
  )
}
