import { useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useMettreAJourProfesseur, useProfesseur } from '@/features/professeurs/hooks/useProfesseurs'
import { useMatieres } from '@/features/referentiel/hooks/useMatieres'
import { useNiveaux } from '@/features/referentiel/hooks/useNiveaux'

export function PageFicheProfesseur() {
  const { id } = useParams<{ id: string }>()
  const professeurId = id ? Number(id) : undefined
  const { data: professeur, isLoading } = useProfesseur(professeurId)
  const { data: matieres } = useMatieres()
  const { data: niveaux } = useNiveaux()
  const mettreAJour = useMettreAJourProfesseur()

  if (isLoading || !professeur) {
    return <p className="p-6 text-sm text-muted-foreground">Chargement…</p>
  }

  const nomMatiere = (matiereId: number) =>
    matieres?.find((m) => m.id === matiereId)?.libelle ?? `Matière #${matiereId}`
  const libelleNiveau = (niveauCode: string) =>
    niveaux?.find((n) => n.code === niveauCode)?.libelle ?? niveauCode

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-medium">
            {professeur.prenom} {professeur.nom}
          </h1>
          <p className="text-sm text-muted-foreground">{professeur.telephone}</p>
        </div>
        <span className="rounded-full border px-2 py-1 text-xs">
          {professeur.actif ? 'Actif' : 'Inactif'}
        </span>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Affectations</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2">Niveau</th>
              <th className="py-2">Matière</th>
              <th className="py-2 text-right">Élèves</th>
            </tr>
          </thead>
          <tbody>
            {professeur.affectations.map((affectation) => (
              <tr key={affectation.id} className="border-b">
                <td className="py-2">{libelleNiveau(affectation.niveau_code)}</td>
                <td className="py-2">{nomMatiere(affectation.matiere_id)}</td>
                <td className="py-2 text-right">{affectation.nombre_eleves}</td>
              </tr>
            ))}
            {professeur.affectations.length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 text-center text-muted-foreground">
                  Aucune affectation.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <Button
        variant="outline"
        disabled={mettreAJour.isPending}
        onClick={() =>
          mettreAJour.mutate({ id: professeur.id, actif: !professeur.actif })
        }
      >
        {professeur.actif ? 'Désactiver' : 'Réactiver'}
      </Button>
    </div>
  )
}
