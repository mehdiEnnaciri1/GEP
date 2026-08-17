import { useState } from 'react'

import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useEleves } from '@/features/eleves/hooks/useEleves'
import type { StatutEleve } from '@/features/eleves/types'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'

const STATUTS: StatutEleve[] = ['ACTIF', 'SUSPENDU', 'ARCHIVE']

export function PageListeEleves() {
  const [recherche, setRecherche] = useState('')
  const [niveauCode, setNiveauCode] = useState('')
  const [statut, setStatut] = useState<StatutEleve | ''>('')
  const [page, setPage] = useState(1)
  const taille = 20

  const { data: niveaux } = useNiveaux()
  const { data, isLoading } = useEleves({
    recherche: recherche || undefined,
    niveau_code: niveauCode || undefined,
    statut: statut || undefined,
    page,
    taille,
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / taille)) : 1

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Élèves</h1>
        <Button asChild>
          <Link to="/eleves/nouveau">Nouvel élève</Link>
        </Button>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Rechercher un nom…"
          value={recherche}
          onChange={(e) => {
            setRecherche(e.target.value)
            setPage(1)
          }}
          className="max-w-xs"
        />
        <select
          className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
          value={niveauCode}
          onChange={(e) => {
            setNiveauCode(e.target.value)
            setPage(1)
          }}
        >
          <option value="">Tous les niveaux</option>
          {niveaux?.map((n) => (
            <option key={n.code} value={n.code}>
              {n.libelle}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-input bg-transparent px-2 py-1 text-sm"
          value={statut}
          onChange={(e) => {
            setStatut(e.target.value as StatutEleve | '')
            setPage(1)
          }}
        >
          <option value="">Tous les statuts</option>
          {STATUTS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Chargement…</p>
      ) : data?.elements.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <img src="/vide-eleves.png" alt="" className="size-32" />
          <p className="text-sm text-muted-foreground">Aucun élève ne correspond à cette recherche.</p>
        </div>
      ) : (
        <>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2">Matricule</th>
                <th className="py-2">Nom</th>
                <th className="py-2">Niveau</th>
                <th className="py-2">Statut</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {data?.elements.map((eleve) => (
                <tr key={eleve.id} className="border-b">
                  <td className="py-2 font-mono text-xs">{eleve.matricule}</td>
                  <td className="py-2">
                    {eleve.nom} {eleve.prenom}
                  </td>
                  <td className="py-2">{eleve.niveau_code}</td>
                  <td className="py-2">{eleve.statut}</td>
                  <td className="py-2 text-right">
                    <Link
                      to={`/eleves/${eleve.id}`}
                      className="text-primary underline-offset-2 hover:underline"
                    >
                      Fiche
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {data?.total ?? 0} élève(s) — page {page}/{totalPages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
