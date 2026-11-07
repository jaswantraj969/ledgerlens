/** Display helpers. The risk score is a heuristic, never shown as a probability. */

export function riskLevel(risk: number | null): 'unknown' | 'low' | 'medium' | 'high' {
  if (risk === null) return 'unknown'
  if (risk < 0.2) return 'low'
  if (risk < 0.5) return 'medium'
  return 'high'
}

export function formatRisk(risk: number | null): string {
  return risk === null ? 'n/a' : risk.toFixed(2)
}

export function formatRate(value: number | null | undefined): string {
  return value === null || value === undefined ? 'n/a' : value.toFixed(3)
}

export function formatInterval(interval: readonly number[] | null | undefined): string {
  return interval ? `[${interval[0].toFixed(3)}, ${interval[1].toFixed(3)}]` : ''
}

const LINE = /^line_items\[(\d+)\]\.(\w+)$/

export function fieldLabel(name: string): string {
  const match = LINE.exec(name)
  const words = (text: string) => text.replace(/_/g, ' ')
  return match ? `Row ${Number(match[1]) + 1}: ${words(match[2])}` : words(name)
}

export const DECISION_LABELS: Record<string, string> = {
  auto_accepted: 'Auto-accepted',
  needs_review: 'Needs review',
  approved: 'Approved',
  corrected: 'Corrected',
  rejected: 'Rejected',
}

export const TERMINAL_STATES = new Set(['ready_for_review', 'completed', 'failed'])
