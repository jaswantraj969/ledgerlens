import { useEffect, useState } from 'react'
import { errorMessage, useApi } from '../api/context'
import type { QueueItem } from '../api/schemas'
import { fieldLabel, formatRisk } from '../lib/format'
import { hrefFor } from '../router'

/** Fields waiting for a person, highest risk first, as the API orders them. */
export function Queue() {
  const api = useApi()
  const [items, setItems] = useState<QueueItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.queue(200).then(setItems).catch((failure) => setError(errorMessage(failure)))
  }, [api])

  if (error) return <p role="alert" className="text-red-700">{error}</p>
  if (!items) return <p>Loading…</p>
  return (
    <section>
      <h2 className="text-xl font-semibold">Review queue</h2>
      <p className="text-sm text-slate-600">
        {items.length} fields, highest heuristic risk first. Risk is a score, not a probability.
      </p>
      {items.length === 0 ? (
        <p className="mt-4">Nothing waits for review.</p>
      ) : (
        <table className="mt-4 w-full text-left text-sm">
          <thead><tr><th>Risk</th><th>Field</th><th>Value</th><th>Document</th></tr></thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.field_id} className="border-t" data-testid="queue-row">
                <td>{formatRisk(item.risk_score)}</td>
                <td>{fieldLabel(item.name)}</td>
                <td className="font-mono">{item.value_raw ?? '—'}</td>
                <td>
                  <a className="underline" href={hrefFor({ page: 'review', documentId: item.document_id })}>
                    {item.filename}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
