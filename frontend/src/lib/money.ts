/**
 * Conversions et formatage des montants monétaires — miroir de
 * `backend/app/shared/money.py`. Tout montant métier est un entier en
 * centimes de dirham (`number` ici, `BIGINT` en base). Ce module est le seul
 * endroit autorisé à diviser un montant par 100 côté front : toute conversion
 * en dirhams, pour affichage ou saisie, passe par ici.
 */

export const CENTS_PAR_DIRHAM = 100
export const DEVISE_PAR_DEFAUT = 'MAD'

/** Espace insécable (U+00A0), construite par code plutôt qu'écrite comme
 * caractère invisible dans le source (ESLint le signalerait de toute façon,
 * `no-irregular-whitespace`). Voir shared/money.py : un export PDF ne doit
 * jamais couper "50,00" et "MAD" sur deux lignes. */
const ESPACE_INSECABLE = String.fromCharCode(0xa0)

/** Réservé à l'affichage — jamais pour un calcul dont le résultat serait
 * renvoyé à l'API en centimes. */
export function centimesVersDirhams(cents: number): number {
  if (!Number.isInteger(cents)) {
    throw new TypeError(`Un montant en centimes doit être un entier, reçu ${cents}.`)
  }
  return cents / CENTS_PAR_DIRHAM
}

/** Convertit une saisie en dirhams (chaîne ou nombre) en centimes, sans
 * jamais multiplier un flottant par 100 : parsing en chaîne, arithmétique
 * entière, arrondi au centime le plus proche (moitié vers le haut) — le
 * même principe que `dirhams_vers_centimes` côté backend, sans `Decimal`. */
export function dirhamsVersCentimes(dirhams: string | number): number {
  const texte = typeof dirhams === 'number' ? dirhams.toString() : dirhams.trim()
  const negatif = texte.startsWith('-')
  const sansSigne = negatif ? texte.slice(1) : texte
  const [entiers = '0', decimales = ''] = sansSigne.split('.')

  if (entiers === '' || !/^\d+$/.test(entiers) || !/^\d*$/.test(decimales)) {
    throw new TypeError(`Montant invalide : ${dirhams}`)
  }

  const decimalesEtendues = (decimales + '000').slice(0, 3)
  let centimes = Number(entiers) * 100 + Number(decimalesEtendues.slice(0, 2))
  if (Number(decimalesEtendues[2]) >= 5) centimes += 1

  return negatif ? -centimes : centimes
}

/** Formate un montant en centimes pour affichage humain : « 12 345,50 MAD ». */
export function formaterMontant(cents: number, devise: string = DEVISE_PAR_DEFAUT): string {
  const dirhams = centimesVersDirhams(Math.abs(cents))
  const signe = cents < 0 ? '-' : ''
  const [entiers, decimales] = dirhams.toFixed(2).split('.')
  return `${signe}${grouperMilliers(entiers)},${decimales}${ESPACE_INSECABLE}${devise}`
}

function grouperMilliers(chiffres: string): string {
  return chiffres.replace(/\B(?=(\d{3})+(?!\d))/g, ESPACE_INSECABLE)
}
