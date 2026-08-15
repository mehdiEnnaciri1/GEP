import type { Matiere, Niveau } from '@/features/referentiel/types'
import type { Affectation, Professeur } from '@/features/professeurs/types'

interface CelluleMatriceProps {
  affectation: Affectation | undefined
  professeurs: Professeur[]
  onAssigner: (professeurId: number) => void
  onRetirer: () => void
  mutationEnCours: boolean
}

function nomProfesseur(professeurs: Professeur[], id: number): string {
  const professeur = professeurs.find((p) => p.id === id)
  return professeur ? `${professeur.prenom} ${professeur.nom}` : `Professeur #${id}`
}

function CelluleMatrice({
  affectation,
  professeurs,
  onAssigner,
  onRetirer,
  mutationEnCours,
}: CelluleMatriceProps) {
  if (affectation) {
    return (
      <div className="flex items-center justify-between gap-2 text-xs">
        <div>
          <div>{nomProfesseur(professeurs, affectation.professeur_id)}</div>
          <div className="text-muted-foreground">{affectation.nombre_eleves} élève(s)</div>
        </div>
        <button
          type="button"
          disabled={mutationEnCours}
          onClick={onRetirer}
          aria-label="Retirer l'affectation"
          className="text-muted-foreground hover:text-destructive"
        >
          ×
        </button>
      </div>
    )
  }

  return (
    <select
      className="w-full rounded border border-input bg-transparent px-1 py-1 text-xs"
      disabled={mutationEnCours}
      value=""
      onChange={(e) => {
        const id = Number(e.target.value)
        if (id) onAssigner(id)
      }}
    >
      <option value="">— Assigner —</option>
      {professeurs
        .filter((p) => p.actif)
        .map((p) => (
          <option key={p.id} value={p.id}>
            {p.prenom} {p.nom}
          </option>
        ))}
    </select>
  )
}

interface MatriceAffectationsProps {
  niveaux: Niveau[]
  matieres: Matiere[]
  professeurs: Professeur[]
  /** clé : `${niveau_code}:${matiere_id}` */
  affectationsParCle: Map<string, Affectation>
  onAssigner: (niveauCode: string, matiereId: number, professeurId: number) => void
  onRetirer: (affectationId: number) => void
  mutationEnCours: boolean
}

/** Grille niveau × matière : chaque cellule vide propose d'assigner un
 * professeur, chaque cellule occupée affiche qui et combien d'élèves — la
 * décision D3 (un seul professeur par couple, voir docs/03-decisions-ouvertes.md)
 * rend cette matrice bijective par construction, pas seulement par convention. */
export function MatriceAffectations({
  niveaux,
  matieres,
  professeurs,
  affectationsParCle,
  onAssigner,
  onRetirer,
  mutationEnCours,
}: MatriceAffectationsProps) {
  return (
    <div className="overflow-x-auto">
      <table className="text-sm">
        <thead>
          <tr>
            <th className="border-b p-2 text-left text-muted-foreground">Niveau \ Matière</th>
            {matieres.map((matiere) => (
              <th key={matiere.id} className="border-b p-2 text-center text-muted-foreground">
                {matiere.libelle}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {niveaux.map((niveau) => (
            <tr key={niveau.code}>
              <th className="border-b p-2 text-left font-normal text-muted-foreground">
                {niveau.libelle}
              </th>
              {matieres.map((matiere) => {
                const cle = `${niveau.code}:${matiere.id}`
                const affectation = affectationsParCle.get(cle)
                return (
                  <td key={matiere.id} className="min-w-[10rem] border-b p-2">
                    <CelluleMatrice
                      affectation={affectation}
                      professeurs={professeurs}
                      mutationEnCours={mutationEnCours}
                      onAssigner={(professeurId) =>
                        onAssigner(niveau.code, matiere.id, professeurId)
                      }
                      onRetirer={() => affectation && onRetirer(affectation.id)}
                    />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
