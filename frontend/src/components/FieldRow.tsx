import { useState, type FormEvent } from 'react'
import { errorMessage, useApi } from '../api/context'
import type { FieldOut } from '../api/schemas'
import { DECISION_LABELS, fieldLabel, formatRisk, riskLevel } from '../lib/format'

interface Props {
  field: FieldOut
  selected: boolean
  canReview: boolean
  onSelect: () => void
  onUpdated: (field: FieldOut) => void
}

const RISK_CLASS = {
  unknown: 'bg-slate-200',
  low: 'bg-green-100 text-green-900',
  medium: 'bg-amber-100 text-amber-900',
  high: 'bg-red-100 text-red-900',
}

export function FieldRow({ field, selected, canReview, onSelect, onUpdated }: Props) {
  const api = useApi()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(field.value_raw ?? '')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const failed = field.validations.filter((check) => !check.passed)

  async function act(action: 'approve' | 'reject' | 'correct', corrected?: string) {
    setBusy(true)
    setError(null)
    try {
      onUpdated(await api.review(field.id, action, corrected))
      setEditing(false)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!value.trim()) {
      setError('Enter the corrected value.')
      return
    }
    void act('correct', value.trim())
  }

  return (
    <li data-testid={`field-${field.name}`} aria-selected={selected}
      className={`rounded border p-2 ${selected ? 'border-amber-500 bg-amber-50' : ''}`}>
      <button type="button" className="w-full text-left" onClick={onSelect}>
        <span className="font-medium">{fieldLabel(field.name)}</span>{' '}
        <span className="font-mono">{field.value_raw ?? '—'}</span>{' '}
        <span className={`ml-1 rounded px-1 text-xs ${RISK_CLASS[riskLevel(field.risk_score)]}`}
          title="Heuristic risk score, not a probability">
          risk {formatRisk(field.risk_score)}
        </span>{' '}
        <span className="text-xs text-slate-600">{DECISION_LABELS[field.decision] ?? field.decision}</span>
      </button>
      <p className="text-xs text-slate-600">
        Source {field.source}; evidence {field.evidence_status}
        {field.evidence_independent ? '' : ' (not independent)'}
        {field.final_value !== null && field.final_value !== field.value_raw && ` → final ${field.final_value}`}
      </p>
      {failed.length > 0 && (
        <ul className="text-xs text-red-700">
          {failed.map((check) => <li key={check.rule_id}>{check.rule_id}: {check.message}</li>)}
        </ul>
      )}
      {canReview && (
        <div className="mt-1 flex gap-2 text-sm">
          <button type="button" disabled={busy} onClick={() => act('approve')}>Approve</button>
          <button type="button" disabled={busy} onClick={() => act('reject')}>Reject</button>
          <button type="button" disabled={busy} onClick={() => setEditing(!editing)}>Correct</button>
        </div>
      )}
      {editing && (
        <form onSubmit={submit} className="mt-1 flex gap-2" aria-label={`Correct ${fieldLabel(field.name)}`}>
          <input aria-label="Corrected value" className="rounded border px-1"
            value={value} onChange={(e) => setValue(e.target.value)} />
          <button type="submit" disabled={busy}>Save</button>
        </form>
      )}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    </li>
  )
}
