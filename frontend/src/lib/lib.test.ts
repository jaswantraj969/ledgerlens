import { describe, expect, it } from 'vitest'
import { roleFromToken } from './auth'
import { hrefFor, parseRoute } from '../router'
import { tokenWithRole } from '../test/fakeApi'
import { fieldLabel, formatInterval, formatRisk, riskLevel } from './format'
import { scaleBox } from './geometry'

describe('scaleBox', () => {
  const page = { width: 400, height: 600 }

  it('scales page units onto the displayed image', () => {
    expect(scaleBox([100, 200, 150, 210], page, 800, 1200)).toEqual({ left: 200, top: 400, width: 100, height: 20 })
  })

  it('draws nothing for missing, inverted or out-of-page boxes', () => {
    expect(scaleBox(null, page, 800, 1200)).toBeNull()
    expect(scaleBox([150, 200, 100, 210], page, 800, 1200)).toBeNull()
    expect(scaleBox([0, 0, 500, 10], page, 800, 1200)).toBeNull()
    expect(scaleBox([1, 2, 3], page, 800, 1200)).toBeNull()
  })
})

describe('format', () => {
  it('bands the heuristic risk score and keeps null distinct', () => {
    expect([riskLevel(0.1), riskLevel(0.3), riskLevel(0.9), riskLevel(null)]).toEqual(['low', 'medium', 'high', 'unknown'])
    expect(formatRisk(null)).toBe('n/a')
    expect(formatRisk(0.25)).toBe('0.25')
  })

  it('labels line-item cells by row', () => {
    expect(fieldLabel('line_items[0].unit_price')).toBe('Row 1: unit price')
    expect(fieldLabel('total_amount')).toBe('total amount')
  })

  it('formats intervals and leaves missing ones empty', () => {
    expect(formatInterval([0.1, 0.25])).toBe('[0.100, 0.250]')
    expect(formatInterval(null)).toBe('')
  })
})

describe('router', () => {
  it('round-trips every route through its href', () => {
    for (const route of [{ page: 'documents' }, { page: 'queue' }, { page: 'report' }, { page: 'review', documentId: 'a b' }] as const) {
      expect(parseRoute(hrefFor(route))).toEqual(route)
    }
  })

  it('falls back to documents for unknown paths', () => {
    expect(parseRoute('#/nope')).toEqual({ page: 'documents' })
  })
})

describe('roleFromToken', () => {
  it('reads the role claim and tolerates junk', () => {
    expect(roleFromToken(tokenWithRole('viewer'))).toBe('viewer')
    expect(roleFromToken('not-a-token')).toBeNull()
    expect(roleFromToken(null)).toBeNull()
  })
})
