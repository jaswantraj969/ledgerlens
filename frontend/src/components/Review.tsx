import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { errorMessage, useApi } from '../api/context'
import type { DocumentFields, FieldOut } from '../api/schemas'
import { saveBlob } from '../lib/download'
import { FieldRow } from './FieldRow'
import { PageViewer } from './PageViewer'

export function Review({ documentId, canReview }: { documentId: string; canReview: boolean }) {
  const api = useApi()
  const [data, setData] = useState<DocumentFields | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [onlyPending, setOnlyPending] = useState(false)

  useEffect(() => {
    let alive = true
    api
      .getFields(documentId)
      .then((result) => alive && setData(result))
      .catch((failure) => {
        if (!alive) return
        setError(failure instanceof ApiError && failure.code === 'not_ready'
          ? 'This document is still being processed.'
          : errorMessage(failure))
      })
    return () => {
      alive = false
    }
  }, [api, documentId])

  function updated(field: FieldOut) {
    setData((current) =>
      current && { ...current, fields: current.fields.map((f) => (f.id === field.id ? field : f)) },
    )
  }

  async function exportAs(format: 'json' | 'csv') {
    try {
      saveBlob(await api.exportDocument(documentId, format), `${documentId}.${format}`)
    } catch (failure) {
      setError(errorMessage(failure))
    }
  }

  if (error) return <p role="alert" className="text-red-700">{error}</p>
  if (!data) return <p>Loading…</p>

  const pending = data.fields.filter((f) => f.decision === 'needs_review').length
  const shown = onlyPending ? data.fields.filter((f) => f.decision === 'needs_review') : data.fields
  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center gap-4">
        <h2 className="text-xl font-semibold">{data.filename}</h2>
        <span className="text-sm">{pending} to review</span>
        <button type="button" onClick={() => exportAs('json')}>Export JSON</button>
        <button type="button" onClick={() => exportAs('csv')}>Export CSV</button>
        <label className="text-sm">
          <input type="checkbox" checked={onlyPending} onChange={(e) => setOnlyPending(e.target.checked)} />{' '}
          Only fields to review
        </label>
      </header>
      {data.degraded_reason && (
        <p role="status" className="rounded bg-amber-100 p-2 text-sm">
          The model was unavailable; these values come from rules ({data.degraded_reason}).
        </p>
      )}
      <div className="flex flex-wrap gap-6">
        <div className="space-y-4">
          {data.pages.map((page) => (
            <PageViewer key={page.number} documentId={documentId} page={page}
              fields={data.fields} selectedId={selected} onSelect={setSelected} />
          ))}
        </div>
        <ul aria-label="Fields" className="min-w-80 flex-1 space-y-2">
          {shown.map((field) => (
            <FieldRow key={field.id} field={field} selected={field.id === selected}
              canReview={canReview} onSelect={() => setSelected(field.id)} onUpdated={updated} />
          ))}
        </ul>
      </div>
    </section>
  )
}
