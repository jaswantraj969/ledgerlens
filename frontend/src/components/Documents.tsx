import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { errorMessage, useApi } from '../api/context'
import type { BatchResult, DocumentOut, JobOut } from '../api/schemas'
import { TERMINAL_STATES } from '../lib/format'
import { hrefFor } from '../router'

export const POLL_MS = 3000

export function Documents({ pollMs = POLL_MS }: { pollMs?: number }) {
  const api = useApi()
  const [documents, setDocuments] = useState<DocumentOut[]>([])
  const [jobs, setJobs] = useState<Record<string, JobOut>>({})
  const [results, setResults] = useState<BatchResult[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments())
      setError(null)
    } catch (failure) {
      setError(errorMessage(failure))
    }
  }, [api])

  // Initial load. State is set only in the promise callbacks, and not after unmount.
  useEffect(() => {
    let active = true
    api.listDocuments().then(
      (list) => {
        if (!active) return
        setDocuments(list)
        setError(null)
      },
      (failure) => {
        if (active) setError(errorMessage(failure))
      },
    )
    return () => {
      active = false
    }
  }, [api])

  // Poll job status for documents still being processed.
  useEffect(() => {
    const pending = documents.filter((d) => !TERMINAL_STATES.has(d.status))
    if (pending.length === 0) return
    const timer = setInterval(async () => {
      const latest = await Promise.all(pending.map((d) => api.getDocument(d.id).catch(() => d)))
      const updated = Object.fromEntries(latest.map((d) => [d.id, d]))
      setDocuments((current) => current.map((d) => updated[d.id] ?? d))
      for (const document of latest) {
        if (document.job_id) {
          const job = await api.getJob(document.job_id).catch(() => null)
          if (job) setJobs((current) => ({ ...current, [document.id]: job }))
        }
      }
    }, pollMs)
    return () => clearInterval(timer)
  }, [api, documents, pollMs])

  async function onFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return
    try {
      const outcome =
        files.length === 1
          ? [{ filename: files[0].name, document: await api.upload(files[0]), error: null, code: null }]
          : await api.uploadBatch(files)
      setResults(outcome)
      await refresh()
    } catch (failure) {
      setResults([{ filename: files[0].name, document: null, error: errorMessage(failure), code: null }])
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Documents</h2>
        <label className="mt-3 inline-block cursor-pointer rounded border px-3 py-2">
          Upload PDF, JPEG or PNG
          <input aria-label="Upload documents" type="file" multiple className="sr-only"
            accept="application/pdf,image/jpeg,image/png" onChange={onFiles} />
        </label>
      </div>
      {results.length > 0 && (
        <ul aria-label="Upload results" className="space-y-1 text-sm">
          {results.map((result, index) => (
            <li key={index} className={result.error ? 'text-red-700' : 'text-green-800'}>
              {result.error
                ? `${result.filename ?? 'File'}: ${result.error}`
                : `${result.document?.filename}: ${result.document?.duplicate ? 'already uploaded' : 'queued'}`}
            </li>
          ))}
        </ul>
      )}
      {error && <p role="alert" className="text-red-700">{error}</p>}
      <table className="w-full text-left text-sm">
        <thead>
          <tr><th>File</th><th>Status</th><th>Pages</th><th>Uploaded</th></tr>
        </thead>
        <tbody>
          {documents.map((document) => {
            const job = jobs[document.id]
            return (
              <tr key={document.id} className="border-t">
                <td>
                  <a className="underline" href={hrefFor({ page: 'review', documentId: document.id })}>
                    {document.filename}
                  </a>
                </td>
                <td data-testid={`status-${document.id}`}>
                  {document.status}
                  {job?.error_code && <span className="ml-2 text-red-700">({job.error_code})</span>}
                </td>
                <td>{document.pages ?? 'n/a'}</td>
                <td>{new Date(document.created_at).toLocaleString()}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {documents.length === 0 && !error && <p className="text-slate-600">No documents yet.</p>}
    </section>
  )
}
