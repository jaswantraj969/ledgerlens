import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('shows the product name and does not imply the review UI exists', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'LedgerLens' })).toBeInTheDocument()
    expect(screen.getByText(/not implemented yet/i)).toBeInTheDocument()
  })
})
