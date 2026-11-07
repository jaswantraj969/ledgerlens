import { vi } from 'vitest'
import { ApiClient, type Fetch } from '../api/client'
import type { DocumentFields, FieldOut } from '../api/schemas'

type Handler = (request: { method: string; path: string; body: unknown }) => Response | Promise<Response>

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** A fetch that routes by "METHOD /path" and records every call. */
export function fakeFetch(routes: Record<string, Handler>) {
  const calls: { method: string; path: string; body: unknown; headers: Headers }[] = []
  const impl = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), 'http://test')
    const path = url.pathname.replace(/^\/api/, '') + url.search
    const method = init.method ?? 'GET'
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body
    calls.push({ method, path, body, headers: new Headers(init.headers) })
    const key = Object.keys(routes).find((route) => {
      const [m, p] = route.split(' ')
      return m === method && (p.endsWith('*') ? path.startsWith(p.slice(0, -1)) : path === p)
    })
    if (!key) return json({ status: 404, title: 'Not found', detail: `no route ${method} ${path}`, code: 'not_found' }, 404)
    return routes[key]({ method, path, body })
  })
  return { fetch: impl as unknown as Fetch, calls }
}

export function client(routes: Record<string, Handler>, onUnauthorized = () => {}) {
  const fake = fakeFetch(routes)
  return { api: new ApiClient('/api', fake.fetch, onUnauthorized), calls: fake.calls }
}

export function field(overrides: Partial<FieldOut> = {}): FieldOut {
  return {
    id: 'f-total', name: 'total_amount', value_raw: '10.000', value_normalized: '10000',
    final_value: null, source: 'llm_pass_a', evidence_status: 'exact', evidence_independent: true,
    risk_score: 0.3, calibrated_prob: null, decision: 'needs_review',
    evidence: [{ page: 1, text: '10.000', bbox: [100, 200, 150, 210], coordinate_system: 'pdf_points_top_left', confidence: 0.9 }],
    validations: [], ...overrides,
  }
}

export function documentFields(fields: FieldOut[] = [field()]): DocumentFields {
  return {
    document_id: 'doc-1', filename: 'receipt.pdf', status: 'ready_for_review',
    run_version: 'rules:0.1.0', provider: 'deterministic', degraded_reason: null,
    pages: [{ number: 1, width: 400, height: 600, coordinate_system: 'pdf_points_top_left', source: 'native_pdf' }],
    fields,
  }
}

export function documentOut(overrides: Record<string, unknown> = {}) {
  return {
    id: 'doc-1', filename: 'receipt.pdf', mime: 'application/pdf', sha256: 'a'.repeat(64),
    status: 'queued', pages: 1, created_at: '2026-11-08T10:00:00Z', duplicate: false,
    job_id: 'job-1', ...overrides,
  }
}

/** A JWT-shaped token with the given role. Unsigned: the UI only reads the role claim. */
export function tokenWithRole(role: string): string {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, '')
  return `${encode({ alg: 'HS256' })}.${encode({ role, sub: 'u1' })}.signature`
}
