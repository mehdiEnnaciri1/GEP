import { useEffect, useState } from 'react'

import { useNavigate } from 'react-router-dom'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreerEleve } from '@/features/eleves/hooks/useEleves'
import { useAnneesScolaires } from '@/features/referentiel/hooks/useAnneesScolaires'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'
import { useTarifsPack } from '@/features/referentiel/hooks/useTarifs'
import { dirhamsVersCentimes, formaterMontant } from '@/lib/money'

const schema = z
  .object({
    nom: z.string().min(1, 'Nom requis'),
    prenom: z.string().min(1, 'Prénom requis'),
    telephone_eleve: z.string().optional(),
    telephone_parent: z.string().min(1, 'Téléphone du parent requis'),
    date_inscription: z.string().min(1, 'Date requise'),
    observation: z.string().optional(),
    niveau_code: z.string().min(1, 'Niveau requis'),
    est_pack: z.boolean(),
    reduction_active: z.boolean(),
    reduction_dh: z.string().optional(),
    matiere_ids: z.array(z.number()),
  })
  .superRefine((donnees, ctx) => {
    if (donnees.matiere_ids.length === 0) {
      ctx.addIssue({
        code: 'custom',
        path: ['matiere_ids'],
        message: 'Choisissez au moins une matière',
      })
    }
    if (donnees.reduction_active && !donnees.reduction_dh?.trim()) {
      ctx.addIssue({ code: 'custom', path: ['reduction_dh'], message: 'Montant requis' })
    }
  })

type Donnees = z.infer<typeof schema>

const ETAPES = ['Identité', 'Niveau', 'Matières'] as const
const CHAMPS_PAR_ETAPE: Record<number, (keyof Donnees)[]> = {
  0: ['nom', 'prenom', 'telephone_parent', 'date_inscription'],
  1: ['niveau_code'],
  2: ['matiere_ids', 'reduction_dh'],
}

export function PageCreationEleve() {
  const navigate = useNavigate()
  const [etape, setEtape] = useState(0)
  const [erreurMontant, setErreurMontant] = useState(false)
  const { data: niveaux } = useNiveaux()
  const { data: matieres } = useMatieres()
  const { data: annees } = useAnneesScolaires()
  const creation = useCreerEleve()

  const anneeActiveId = annees?.find((a) => a.est_active)?.id
  const { data: tarifsPack } = useTarifsPack(anneeActiveId)

  const {
    register,
    handleSubmit,
    trigger,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Donnees>({
    resolver: zodResolver(schema),
    defaultValues: { matiere_ids: [], est_pack: false, reduction_active: false },
  })

  const matiereIds = watch('matiere_ids')
  const estPack = watch('est_pack')
  const reductionActive = watch('reduction_active')
  const niveauCode = watch('niveau_code')

  const matieresActives = matieres?.filter((m) => m.actif) ?? []
  const tarifPackNiveau = tarifsPack?.find((t) => t.niveau_code === niveauCode)

  // Pack coché : toutes les matières actives sont sélectionnées et grisées —
  // pas de choix à faire, voir EleveService.creer (composé automatiquement
  // depuis les tarifs du niveau).
  useEffect(() => {
    if (estPack) {
      setValue(
        'matiere_ids',
        matieresActives.map((m) => m.id),
        { shouldValidate: true },
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estPack, matieres])

  const suivant = async () => {
    const valide = await trigger(CHAMPS_PAR_ETAPE[etape])
    if (valide) setEtape((e) => Math.min(e + 1, ETAPES.length - 1))
  }

  const precedent = () => setEtape((e) => Math.max(e - 1, 0))

  const onSubmit = handleSubmit((donnees) => {
    setErreurMontant(false)
    let reduction_mensuelle_cents: number | undefined
    if (donnees.reduction_active) {
      try {
        reduction_mensuelle_cents = dirhamsVersCentimes(donnees.reduction_dh ?? '')
      } catch {
        setErreurMontant(true)
        return
      }
    }

    creation.mutate(
      {
        nom: donnees.nom,
        prenom: donnees.prenom,
        telephone_eleve: donnees.telephone_eleve,
        telephone_parent: donnees.telephone_parent,
        niveau_code: donnees.niveau_code,
        date_inscription: donnees.date_inscription,
        observation: donnees.observation,
        est_pack: donnees.est_pack,
        reduction_mensuelle_cents,
        matiere_ids: donnees.matiere_ids,
      },
      { onSuccess: (eleve) => navigate(`/eleves/${eleve.id}`) },
    )
  })

  const basculerMatiere = (id: number) => {
    const actuel = matiereIds ?? []
    setValue(
      'matiere_ids',
      actuel.includes(id) ? actuel.filter((m) => m !== id) : [...actuel, id],
      { shouldValidate: true },
    )
  }

  const basculerPack = () => {
    setValue('est_pack', !estPack, { shouldValidate: true })
    if (!estPack) setValue('reduction_active', false)
  }

  const basculerReduction = () => {
    setValue('reduction_active', !reductionActive, { shouldValidate: true })
    if (!reductionActive) setValue('est_pack', false)
  }

  return (
    <div className="mx-auto max-w-xl space-y-6 p-6">
      <h1 className="text-lg font-medium">Nouvel élève</h1>

      <div className="flex gap-2 text-sm">
        {ETAPES.map((libelle, i) => (
          <span
            key={libelle}
            className={i === etape ? 'font-medium text-foreground' : 'text-muted-foreground'}
          >
            {i > 0 && ' → '}
            {libelle}
          </span>
        ))}
      </div>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {etape === 0 && (
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="nom">Nom</Label>
              <Input id="nom" {...register('nom')} />
              {errors.nom && <p className="text-xs text-destructive">{errors.nom.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="prenom">Prénom</Label>
              <Input id="prenom" {...register('prenom')} />
              {errors.prenom && (
                <p className="text-xs text-destructive">{errors.prenom.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="telephone_parent">Téléphone du parent</Label>
              <Input id="telephone_parent" {...register('telephone_parent')} />
              {errors.telephone_parent && (
                <p className="text-xs text-destructive">{errors.telephone_parent.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="telephone_eleve">Téléphone de l'élève (optionnel)</Label>
              <Input id="telephone_eleve" {...register('telephone_eleve')} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="date_inscription">Date d'inscription</Label>
              <Input id="date_inscription" type="date" {...register('date_inscription')} />
              {errors.date_inscription && (
                <p className="text-xs text-destructive">{errors.date_inscription.message}</p>
              )}
            </div>
          </div>
        )}

        {etape === 1 && (
          <div className="space-y-1">
            <Label htmlFor="niveau_code">Niveau</Label>
            <select
              id="niveau_code"
              className="w-full rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
              {...register('niveau_code')}
            >
              <option value="">Choisir…</option>
              {niveaux?.map((n) => (
                <option key={n.code} value={n.code}>
                  {n.libelle}
                </option>
              ))}
            </select>
            {errors.niveau_code && (
              <p className="text-xs text-destructive">{errors.niveau_code.message}</p>
            )}
          </div>
        )}

        {etape === 2 && (
          <div className="space-y-4">
            <div className="space-y-2 rounded-lg border p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={estPack} onChange={basculerPack} />
                Pack — toutes les matières du niveau
              </label>
              {estPack && (
                <p className="pl-6 text-xs text-muted-foreground">
                  {tarifPackNiveau
                    ? `Forfait pack pour ce niveau : ${formaterMontant(tarifPackNiveau.montant_cents)} / mois.`
                    : "Aucun tarif pack défini pour ce niveau — définissez-le dans le référentiel avant de valider."}
                </p>
              )}

              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={reductionActive} onChange={basculerReduction} />
                Réduction — montant mensuel personnalisé
              </label>
              {reductionActive && (
                <div className="space-y-1 pt-1 pl-6">
                  <Label htmlFor="reduction_dh">Montant mensuel fixe (DH)</Label>
                  <Input
                    id="reduction_dh"
                    inputMode="decimal"
                    className="w-32"
                    {...register('reduction_dh')}
                  />
                  {errors.reduction_dh && (
                    <p className="text-xs text-destructive">{errors.reduction_dh.message}</p>
                  )}
                  {erreurMontant && <p className="text-xs text-destructive">Montant invalide.</p>}
                </div>
              )}

              <p className="pt-1 text-xs text-muted-foreground">
                La réduction remplace le calcul par matière et reste fixe toute l'année. Les
                matières cochées ci-dessous servent à savoir dans quels cours l'élève est
                présent — elles restent utilisées pour la paie des professeurs.
              </p>
            </div>

            <div className="space-y-2">
              {matieresActives.map((matiere) => (
                <label key={matiere.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={matiereIds?.includes(matiere.id) ?? false}
                    disabled={estPack}
                    onChange={() => basculerMatiere(matiere.id)}
                  />
                  {matiere.libelle}
                </label>
              ))}
              {errors.matiere_ids && (
                <p className="text-xs text-destructive">{errors.matiere_ids.message}</p>
              )}
            </div>
          </div>
        )}

        {creation.isError && (
          <p className="text-sm text-destructive" role="alert">
            {creation.error instanceof ErreurApi
              ? creation.error.message
              : 'Une erreur est survenue.'}
          </p>
        )}

        <div className="flex justify-between pt-2">
          <Button type="button" variant="outline" onClick={precedent} disabled={etape === 0}>
            Précédent
          </Button>
          {etape < ETAPES.length - 1 ? (
            <Button type="button" onClick={suivant}>
              Suivant
            </Button>
          ) : (
            <Button type="submit" disabled={creation.isPending}>
              Créer l'élève
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}
