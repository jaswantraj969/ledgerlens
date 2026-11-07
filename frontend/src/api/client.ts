import type { z } from 'zod'
import * as s from './schemas'

export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export type Fetch = typeof fetch
export type ReviewAction = 'approve' | 'reject' | 'correct'

const TOKEN_KEY = 'ledgerlens.access_token'

/** Tokens live in sessionStorage: gone when the tab closes, never in localStorage. */
export const tokenStore = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string | null): void {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      // Storage can be blocked; the session then lasts only for this page.
    }
  },
}

export class ApiClient {
  private readonly baseUrl: string
  private readonly fetchImpl: Fetch
  private readonly onUnauthorized: () => void

  constructor(baseUrl = '/api', fetchImpl: Fetch = fetch.bind(globalThis), onUnauthorized = () => {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.fetchImpl = fetchImpl
    this.onUnauthorized = onUnauthorized
  }

  private async raw(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers)
    const token = tokenStore.get()
    if (token) headers.set('Authorization', `Bearer ${token}`)
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, { ...init, headers })
    if (!response.ok) {
      if (response.status === 401) {
        tokenStore.set(null)
        this.onUnauthorized()
      }
      throw await toError(response)
    }
    return response
  }

  private async json<T>(schema: z.ZodType<T>, path: string, init?: RequestInit): Promise<T> {
    const response = await this.raw(path, init)
    return schema.parse(await response.json())
  }

  private post<T>(schema: z.ZodType<T>, path: string, body: unknown): Promise<T> {
    return this.json(schema, path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  async login(email: string, password: string): Promise<void> {
    const result = await this.post(s.tokens, '/auth/login', { email, password })
    tokenStore.set(result.access_token)
  }

  logout(): void {
    tokenStore.set(null)
  }

  listDocuments(limit = 50, offset = 0): Promise<s.DocumentOut[]> {
    return this.json(s.documentSchema.array(), `/documents?limit=${limit}&offset=${offset}`)
  }

  getDocument(id: string): Promise<s.DocumentOut> {
    return this.json(s.documentSchema, `/documents/${encodeURIComponent(id)}`)
  }

  upload(file: File): Promise<s.DocumentOut> {
    const form = new FormData()
    form.append('file', file)
    return this.json(s.documentSchema, '/documents', { method: 'POST', body: form })
  }

  uploadBatch(files: File[]): Promise<s.BatchResult[]> {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    return this.json(s.batchResult.array(), '/documents/batch', { method: 'POST', body: form })
  }

  getJob(id: string): Promise<s.JobOut> {
    return this.json(s.jobSchema, `/jobs/${encodeURIComponent(id)}`)
  }

  getFields(documentId: string): Promise<s.DocumentFields> {
    return this.json(s.documentFields, `/documents/${encodeURIComponent(documentId)}/fields`)
  }

  review(fieldId: string, action: ReviewAction, value?: string): Promise<s.FieldOut> {
    const body = action === 'correct' ? { action, value } : { action }
    return this.post(s.fieldSchema, `/fields/${encodeURIComponent(fieldId)}/review`, body)
  }

  queue(limit = 50): Promise<s.QueueItem[]> {
    return this.json(s.queueItem.array(), `/review/queue?limit=${limit}`)
  }

  /** Page images need the auth header, so they are fetched as blobs, not linked. */
  async pageImage(documentId: string, page: number): Promise<Blob> {
    const response = await this.raw(`/documents/${encodeURIComponent(documentId)}/pages/${page}/image`)
    return response.blob()
  }

  async exportDocument(documentId: string, format: 'json' | 'csv'): Promise<Blob> {
    const response = await this.raw(`/documents/${encodeURIComponent(documentId)}/export?format=${format}`)
    return response.blob()
  }

  report(): Promise<s.Report> {
    return this.json(s.report, '/evaluation/report')
  }
}

async function toError(response: Response): Promise<ApiError> {
  try {
    const body = s.problem.parse(await response.json())
    return new ApiError(response.status, body.detail ?? body.title, body.code)
  } catch {
    return new ApiError(response.status, `Request failed (${response.status})`)
  }
}
