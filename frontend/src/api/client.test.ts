import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, tokenStore } from './client'
import { client, documentFields, json } from '../test/fakeApi'

beforeEach(() => sessionStorage.clear())

describe('ApiClient', () => {
  it('stores the access token on login and sends it afterwards', async () => {
    const { api, calls } = client({
      'POST /auth/login': () => json({ access_token: 'tok', refresh_token: 'r', token_type: 'bearer' }),
      'GET /documents?limit=50&offset=0': () => json([]),
    })
    await api.login('a@b.test', 'pw')
    expect(tokenStore.get()).toBe('tok')
    await api.listDocuments()
    expect(calls[1].headers.get('Authorization')).toBe('Bearer tok')
    expect(calls[0].body).toEqual({ email: 'a@b.test', password: 'pw' })
  })

  it('turns problem responses into ApiError with the code and detail', async () => {
    const { api } = client({
      'POST /fields/f1/review': () =>
        json({ status: 422, title: 'Invalid review', detail: 'A correction needs a value.', code: 'value_required' }, 422),
    })
    const error = await api.review('f1', 'correct', '').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'value_required', message: 'A correction needs a value.' })
  })

  it('clears the session and reports when the server answers 401', async () => {
    tokenStore.set('old')
    const onUnauthorized = vi.fn()
    const { api } = client({ 'GET /review/queue?limit=50': () => json({ status: 401, title: 'Not authenticated' }, 401) }, onUnauthorized)
    await expect(api.queue()).rejects.toBeInstanceOf(ApiError)
    expect(tokenStore.get()).toBeNull()
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('rejects a response that does not match the schema instead of passing it on', async () => {
    const { api } = client({ 'GET /documents/d/fields': () => json({ document_id: 'd' }) })
    await expect(api.getFields('d')).rejects.toThrow()
  })

  it('sends only the action unless it is a correction', async () => {
    const reply = () => json(documentFields().fields[0])
    const { api, calls } = client({ 'POST /fields/f/review': reply })
    await api.review('f', 'approve')
    await api.review('f', 'correct', '9.99')
    expect(calls.map((c) => c.body)).toEqual([{ action: 'approve' }, { action: 'correct', value: '9.99' }])
  })

  it('uploads one file as "file" and a batch as "files"', async () => {
    const { api, calls } = client({
      'POST /documents': () => json({ id: 'd', filename: 'a.pdf', mime: 'application/pdf', sha256: 'x', status: 'queued', pages: 1, created_at: 'now', duplicate: false, job_id: 'j' }, 201),
      'POST /documents/batch': () => json([]),
    })
    await api.upload(new File(['%PDF'], 'a.pdf'))
    await api.uploadBatch([new File(['%PDF'], 'a.pdf'), new File(['%PDF'], 'b.pdf')])
    expect((calls[0].body as FormData).getAll('file')).toHaveLength(1)
    expect((calls[1].body as FormData).getAll('files')).toHaveLength(2)
  })

  it('escapes ids in paths', async () => {
    const { api, calls } = client({ 'GET /jobs/*': () => json({}) })
    await api.getJob('a/b').catch(() => undefined)
    expect(calls[0].path).toBe('/jobs/a%2Fb')
  })
})
