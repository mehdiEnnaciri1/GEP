import { describe, expect, it } from 'vitest'

import { centimesVersDirhams, dirhamsVersCentimes, formaterMontant } from './money'

const ESPACE_INSECABLE = String.fromCharCode(0xa0)

describe('centimesVersDirhams', () => {
  it('convertit un montant rond', () => {
    expect(centimesVersDirhams(5000)).toBe(50)
  })

  it('convertit un montant avec centimes', () => {
    expect(centimesVersDirhams(150)).toBe(1.5)
  })

  it('refuse un montant non entier', () => {
    expect(() => centimesVersDirhams(50.5)).toThrow(TypeError)
  })
})

describe('dirhamsVersCentimes', () => {
  it('convertit depuis une chaîne', () => {
    expect(dirhamsVersCentimes('50')).toBe(5000)
  })

  it('convertit depuis un nombre', () => {
    expect(dirhamsVersCentimes(35.5)).toBe(3550)
  })

  it('arrondit la troisième décimale vers le haut', () => {
    expect(dirhamsVersCentimes('35.999')).toBe(3600)
  })

  it('arrondit un demi-centime vers le haut', () => {
    expect(dirhamsVersCentimes('0.005')).toBe(1)
  })

  it('gère les montants négatifs', () => {
    expect(dirhamsVersCentimes('-5')).toBe(-500)
  })

  it('refuse un montant invalide', () => {
    expect(() => dirhamsVersCentimes('pas-un-montant')).toThrow(TypeError)
  })

  it('aller-retour exact avec centimesVersDirhams', () => {
    const cents = dirhamsVersCentimes('35.50')
    expect(centimesVersDirhams(cents)).toBe(35.5)
  })
})

describe('formaterMontant', () => {
  it('formate un montant simple', () => {
    expect(formaterMontant(5000)).toBe(`50,00${ESPACE_INSECABLE}MAD`)
  })

  it('groupe les milliers', () => {
    expect(formaterMontant(1_234_550)).toBe(`12${ESPACE_INSECABLE}345,50${ESPACE_INSECABLE}MAD`)
  })

  it('gère un montant négatif', () => {
    expect(formaterMontant(-5000)).toBe(`-50,00${ESPACE_INSECABLE}MAD`)
  })

  it('accepte une devise personnalisée', () => {
    expect(formaterMontant(5000, 'EUR')).toBe(`50,00${ESPACE_INSECABLE}EUR`)
  })

  it('reproduit l’exemple de paie du §7.2', () => {
    expect(formaterMontant(75_000)).toBe(`750,00${ESPACE_INSECABLE}MAD`)
  })
})
