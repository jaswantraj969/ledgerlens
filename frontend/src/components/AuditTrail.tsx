import { useEffect, useState } from 'react'
import { errorMessage, useApi } from '../api/context'
import type { AuditEvent } from '../api/schemas'
import { fieldLabel } from '../lib/format'

const ACTION_LABELS: Record<string, string> = {
  'document.upload': 'Uploaded',
  'field.approve': 'Approved',
  'field.reject': 'Rejected',
  'field.correct': 'Corrected',
}

const show = (value: string | null) => value ?? '(none)'

/** The document's stored audit events, newest first. Read-only. `version` changes reload it. */
export function AuditTrail({ documentId, version }: { documentId: string; version: number }) {
  const api = useApi()
  const [events, setEvents] = useState<AuditEvent[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    api.auditTrail(documentId).then(
      (result) => {
        if (!alive) return
        setEvents(result)
        setError(null)
      },
      (failure) => {
        if (alive) setError(errorMessage(failure))
      },
    )
    return () => {
      alive = false
    }
  }, [api, documentId, version])

  return (
    <section aria-label="Audit trail" className="space-y-2">
      <h3 className="text-lg font-semibold">Audit trail</h3>
      {error && <p className="text-sm text-red-700">Audit trail unavailable: {error}</p>}
      {!error && events === null && <p className="text-sm">Loading…</p>}
      {events && events.length === 0 && <p className="text-sm text-slate-600">No events yet.</p>}
      {events && events.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr><th>When</th><th>Who</th><th>Action</th><th>Field</th><th>Old value</th><th>New value</th></tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id} data-testid="audit-event" className="border-t">
                <td>{new Date(event.created_at).toLocaleString()}</td>
                <td>{event.actor_email ?? 'system'}</td>
                <td>{ACTION_LABELS[event.action] ?? event.action}</td>
                <td>{event.field_name ? fieldLabel(event.field_name) : 'document'}</td>
                <td>{event.entity === 'field' ? show(event.old_value) : ''}</td>
                <td>{event.entity === 'field' ? show(event.new_value) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
