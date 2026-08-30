import { useState } from 'react'

import { Building2Icon, CalculatorIcon, SettingsIcon, TagIcon, type LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useMettreAJourParametre, useParametres } from '@/features/referentiel/hooks/useParametres'
import { centimesVersDirhams, dirhamsVersCentimes } from '@/lib/money'

const ICONES: Record<string, LucideIcon> = {
  nom_centre: Building2Icon,
  frais_inscription_cents: TagIcon,
  base_calcul_paie: CalculatorIcon,
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

function LigneBaseCalculPaie({ valeur }: { valeur: string; description: string | null }) {
  const miseAJour = useMettreAJourParametre()

  const OPTIONS: { valeur: string; libelle: string }[] = [
    { valeur: 'inscrits', libelle: 'Inscrits' },
    { valeur: 'payants', libelle: 'Payants' },
  ]

  return (
    <div className="space-y-2 py-4">
      <div className="flex flex-wrap items-center gap-4">
        <EnTeteParametre cle="base_calcul_paie" description="inscrits | payants — voir décision D4" />
        <div className="flex gap-1.5 rounded-lg bg-muted p-1">
          {OPTIONS.map((option) => (
            <Button
              key={option.valeur}
              type="button"
              size="sm"
              variant={valeur === option.valeur ? 'default' : 'ghost'}
              disabled={miseAJour.isPending}
              onClick={() => miseAJour.mutate({ cle: 'base_calcul_paie', valeur: option.valeur })}
            >
              {option.libelle}
            </Button>
          ))}
        </div>
      </div>
      <p className="pl-13 text-xs text-muted-foreground">
        <span className="font-medium">N.B.</span> — décide si un professeur est payé pour un
        élève qui n'a pas encore réglé le mois. <span className="font-medium">Inscrits</span> :
        tous les élèves actifs de la matière/niveau comptent, payés ou non (le cours a été
        donné). <span className="font-medium">Payants</span> : seuls les élèves dont
        l'échéance du mois est payée (totalement ou en partie) comptent — un élève non payé ne
        rapporte rien au professeur ce mois-là. Le changement s'applique à la prochaine
        génération de paie, jamais aux paies déjà créées.
      </p>
    </div>
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
              if (parametre.cle === 'base_calcul_paie') {
                return (
                  <LigneBaseCalculPaie
                    key={parametre.cle}
                    valeur={parametre.valeur}
                    description={parametre.description}
                  />
                )
              }
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
