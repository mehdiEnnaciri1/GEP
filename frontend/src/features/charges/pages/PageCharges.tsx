import { useState } from 'react'

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { ErreurApi } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApercuJustificatif } from '@/features/charges/components/ApercuJustificatif'
import { GraphiqueChargesParCategorie } from '@/features/charges/components/GraphiqueChargesParCategorie'
import {
  useAnnulerCharge,
  useCategoriesCharge,
  useCharges,
  useCreerCategorieCharge,
  useCreerCharge,
  useTotauxCharges,
} from '@/features/charges/hooks/useCharges'
import { dirhamsVersCentimes, formaterMontant } from '@/lib/money'

const MODES_PAIEMENT = ['ESPECES', 'VIREMENT', 'CHEQUE', 'CARTE', 'AUTRE'] as const

const schema = z.object({
  categorie_id: z.string().min(1, 'Catégorie requise'),
  description: z.string().min(1, 'Description requise'),
  montant: z.string().min(1, 'Montant requis'),
  date_charge: z.string().min(1, 'Date requise'),
  periode: z.string().min(7, 'Période requise (YYYY-MM)').max(7),
  mode_paiement: z.enum(MODES_PAIEMENT),
})

type Donnees = z.infer<typeof schema>

function periodeCourante(): string {
  const maintenant = new Date()
  return `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, '0')}`
}

export function PageCharges() {
  const [periodeFiltre, setPeriodeFiltre] = useState(periodeCourante())
  const [categorieFiltre, setCategorieFiltre] = useState<number | undefined>(undefined)
  const [formulaireOuvert, setFormulaireOuvert] = useState(false)
  const [fichier, setFichier] = useState<File | null>(null)
  const [nouvelleCategorie, setNouvelleCategorie] = useState('')
  const [apercuChargeId, setApercuChargeId] = useState<number | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  const { data: categories } = useCategoriesCharge()
  const { data: charges, isLoading } = useCharges({
    periode: periodeFiltre || undefined,
    categorie_id: categorieFiltre,
  })
  const { data: totaux, isLoading: totauxEnCours } = useTotauxCharges(periodeFiltre || undefined)
  const creation = useCreerCharge()
  const creationCategorie = useCreerCategorieCharge()
  const annulation = useAnnulerCharge()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Donnees>({
    resolver: zodResolver(schema),
    defaultValues: { periode: periodeCourante(), mode_paiement: 'VIREMENT' },
  })

  const nomCategorie = (categorieId: number) =>
    categories?.find((c) => c.id === categorieId)?.libelle ?? `Catégorie #${categorieId}`

  const onSubmit = handleSubmit((donnees) => {
    setErreur(null)
    creation.mutate(
      {
        categorie_id: Number(donnees.categorie_id),
        description: donnees.description,
        montant_cents: dirhamsVersCentimes(donnees.montant),
        date_charge: donnees.date_charge,
        periode: donnees.periode,
        mode_paiement: donnees.mode_paiement,
        justificatif: fichier,
      },
      {
        onSuccess: () => {
          reset({ periode: periodeFiltre, mode_paiement: 'VIREMENT' })
          setFichier(null)
          setFormulaireOuvert(false)
        },
        onError: (err) =>
          setErreur(err instanceof ErreurApi ? err.message : 'Erreur lors de la création.'),
      },
    )
  })

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Charges du centre</h1>
        <Button variant="outline" onClick={() => setFormulaireOuvert((o) => !o)}>
          {formulaireOuvert ? 'Annuler' : 'Nouvelle charge'}
        </Button>
      </div>

      {formulaireOuvert && (
        <form onSubmit={onSubmit} noValidate className="space-y-3 rounded-lg border p-4">
          <div className="flex items-end gap-2">
            <div className="flex-1 space-y-1">
              <Label htmlFor="categorie_id">Catégorie</Label>
              <select
                id="categorie_id"
                className="w-full rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
                {...register('categorie_id')}
              >
                <option value="">Choisir…</option>
                {categories
                  ?.filter((c) => c.actif)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.libelle}
                    </option>
                  ))}
              </select>
              {errors.categorie_id && (
                <p className="text-xs text-destructive">{errors.categorie_id.message}</p>
              )}
            </div>
            <div className="flex items-end gap-2">
              <Input
                placeholder="Nouvelle catégorie…"
                value={nouvelleCategorie}
                onChange={(e) => setNouvelleCategorie(e.target.value)}
                className="w-40"
              />
              <Button
                type="button"
                variant="outline"
                disabled={!nouvelleCategorie.trim() || creationCategorie.isPending}
                onClick={() => {
                  creationCategorie.mutate(nouvelleCategorie.trim(), {
                    onSuccess: () => setNouvelleCategorie(''),
                  })
                }}
              >
                Ajouter
              </Button>
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="description">Description</Label>
            <Input id="description" {...register('description')} />
            {errors.description && (
              <p className="text-xs text-destructive">{errors.description.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="montant">Montant (DH)</Label>
              <Input id="montant" inputMode="decimal" {...register('montant')} />
              {errors.montant && (
                <p className="text-xs text-destructive">{errors.montant.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="mode_paiement">Mode de paiement</Label>
              <select
                id="mode_paiement"
                className="w-full rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
                {...register('mode_paiement')}
              >
                {MODES_PAIEMENT.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="date_charge">Date de la charge</Label>
              <Input id="date_charge" type="date" {...register('date_charge')} />
              {errors.date_charge && (
                <p className="text-xs text-destructive">{errors.date_charge.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="periode">Mois concerné (YYYY-MM)</Label>
              <Input id="periode" {...register('periode')} />
              {errors.periode && (
                <p className="text-xs text-destructive">{errors.periode.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="justificatif">Justificatif (JPEG, PNG ou PDF — optionnel)</Label>
            <input
              id="justificatif"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
              className="block w-full text-sm"
            />
          </div>

          {erreur && (
            <p className="text-sm text-destructive" role="alert">
              {erreur}
            </p>
          )}

          <Button type="submit" disabled={creation.isPending}>
            Enregistrer
          </Button>
        </form>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="filtre-periode">Période</Label>
          <Input
            id="filtre-periode"
            value={periodeFiltre}
            onChange={(e) => setPeriodeFiltre(e.target.value)}
            className="w-28"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="filtre-categorie">Catégorie</Label>
          <select
            id="filtre-categorie"
            className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
            value={categorieFiltre ?? ''}
            onChange={(e) => setCategorieFiltre(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">Toutes les catégories</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.libelle}
              </option>
            ))}
          </select>
        </div>
        {totaux && (
          <p className="text-sm text-muted-foreground">
            Total {periodeFiltre} : <span className="font-medium">{formaterMontant(totaux.total_cents)}</span>
          </p>
        )}
      </div>

      {periodeFiltre && (
        <GraphiqueChargesParCategorie
          totaux={totaux}
          categories={categories}
          periode={periodeFiltre}
          isLoading={totauxEnCours}
        />
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Date</th>
              <th className="py-2">Catégorie</th>
              <th className="py-2">Description</th>
              <th className="py-2 text-right">Montant</th>
              <th className="py-2" />
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {charges?.map((charge) => (
              <tr key={charge.id} className="border-b">
                <td className="py-2">{charge.date_charge}</td>
                <td className="py-2">{nomCategorie(charge.categorie_id)}</td>
                <td className="py-2">{charge.description}</td>
                <td className="py-2 text-right">{formaterMontant(charge.montant_cents)}</td>
                <td className="py-2 text-right">
                  {charge.justificatif_type && (
                    <button
                      type="button"
                      className="text-primary underline-offset-2 hover:underline"
                      onClick={() => setApercuChargeId(charge.id)}
                    >
                      Justificatif
                    </button>
                  )}
                </td>
                <td className="py-2 text-right">
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-destructive"
                    disabled={annulation.isPending}
                    onClick={() => annulation.mutate(charge.id)}
                  >
                    Annuler
                  </button>
                </td>
              </tr>
            ))}
            {charges?.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-muted-foreground">
                  Aucune charge pour cette sélection.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {apercuChargeId !== null && (
        <ApercuJustificatif chargeId={apercuChargeId} onFermer={() => setApercuChargeId(null)} />
      )}
    </div>
  )
}
