import { useState } from 'react'

import { Building2Icon, SettingsIcon, TagIcon, type LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useMettreAJourParametre, useParametres } from '@/features/referentiel/hooks/useParametres'
import { centimesVersDirhams, dirhamsVersCentimes } from '@/lib/money'

const ICONES: Record<string, LucideIcon> = {
  nom_centre: Building2Icon,
  frais_inscription_cents: TagIcon,
}

function EnTeteParametre({ cle, description }: { cle: string; description: string | null }) {
  const Icone = ICONES[cle] ?? SettingsIcon
  return (
    <>
      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        <Icone className="size-4" />
      </div>
      <div className="min-w-48 flex-1">
        <p className="font-mono text-xs font-medium">{cle}</p>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
    </>
  )
}

function LigneFraisInscription({ valeur }: { valeur: string; description: string | null }) {
  // La valeur stockée reste en centimes (règle du projet, voir shared/money.py
  // / lib/money.ts) — seule la saisie/l'affichage passe en DH ici.
  const valeurDh = String(centimesVersDirhams(Number(valeur)))
  const [brouillon, setBrouillon] = useState(valeurDh)
  const [erreur, setErreur] = useState(false)
  const miseAJour = useMettreAJourParametre()

  const modifie = brouillon !== valeurDh

  return (
    <div className="flex flex-wrap items-center gap-4 py-4">
      <EnTeteParametre
        cle="frais_inscription_cents"
        description="Frais d'inscription unique, en DH"
      />
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5">
          <Input
            value={brouillon}
            onChange={(e) => {
              setBrouillon(e.target.value)
              setErreur(false)
            }}
            inputMode="decimal"
            className="w-28 bg-card"
          />
          <span className="text-sm text-muted-foreground">DH</span>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={!modifie || miseAJour.isPending}
          onClick={() => {
            try {
              const cents = dirhamsVersCentimes(brouillon)
              miseAJour.mutate({ cle: 'frais_inscription_cents', valeur: String(cents) })
            } catch {
              setErreur(true)
            }
          }}
        >
          {miseAJour.isPending ? 'Enregistrement…' : 'Enregistrer'}
        </Button>
      </div>
      {erreur && <p className="w-full text-xs text-destructive">Montant invalide.</p>}
    </div>
  )
}

function LigneParametreTexte({
  cle,
  valeur,
  description,
}: {
  cle: string
  valeur: string
  description: string | null
}) {
  const [brouillon, setBrouillon] = useState(valeur)
  const miseAJour = useMettreAJourParametre()

  const modifie = brouillon !== valeur

  return (
    <div className="flex flex-wrap items-center gap-4 py-4">
      <EnTeteParametre cle={cle} description={description} />
      <div className="flex items-center gap-2">
        <Input
          value={brouillon}
          onChange={(e) => setBrouillon(e.target.value)}
          className="w-40 bg-card"
        />
        <Button
          size="sm"
          variant="outline"
          disabled={!modifie || miseAJour.isPending}
          onClick={() => miseAJour.mutate({ cle, valeur: brouillon })}
        >
          {miseAJour.isPending ? 'Enregistrement…' : 'Enregistrer'}
        </Button>
      </div>
    </div>
  )
}

export function PageParametres() {
  const { data: parametres, isLoading } = useParametres()

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="font-heading text-xl font-semibold">Paramètres</h1>
        <p className="text-sm text-muted-foreground">Réglages globaux du centre.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Général</CardTitle>
          <CardDescription>Ces valeurs s'appliquent à tout le centre.</CardDescription>
        </CardHeader>
        <CardContent className="divide-y">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="my-2 h-12 rounded-lg" />)
          ) : (
            parametres?.map((parametre) => {
              if (parametre.cle === 'frais_inscription_cents') {
                return (
                  <LigneFraisInscription
                    key={parametre.cle}
                    valeur={parametre.valeur}
                    description={parametre.description}
                  />
                )
              }
              return (
                <LigneParametreTexte
                  key={parametre.cle}
                  cle={parametre.cle}
                  valeur={parametre.valeur}
                  description={parametre.description}
                />
              )
            })
          )}
        </CardContent>
      </Card>
    </div>
  )
}
