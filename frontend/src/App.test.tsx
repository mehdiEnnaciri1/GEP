import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('affiche la page racine', () => {
    render(<App />)
    expect(screen.getByText(/GEP/)).toBeInTheDocument()
  })
})
