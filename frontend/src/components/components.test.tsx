import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import type { ApiClient } from '../api/client'
import { tokenStore } from '../api/client'
import { ApiContext } from '../api/context'
import { client, documentFields, documentOut, field, json, tokenWithRole } from '../test/fakeApi'
import { Documents } from './Documents'
import { Login } from './Login'
import { Queue } from './Queue'
import { Report } from './Report'
import { Review } from './Review'

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => 'blob:page')
  URL.revokeObjectURL = vi.fn()
})
beforeEach(() => {
  sessionStorage.clear()
  window.location.hash = ''
})

function withApi(api: ApiClient, node: ReactNode) {
  return render(<ApiContext.Provider value={api}>{node}</ApiContext.Provider>)
}

const image = () => new Response('png-bytes', { status: 200, headers: { 'Content-Type': 'image/png' } })

describe('Login', () => {
  it('signs in and reports success', async () => {
    const { api } = client({ 'POST /auth/login': () => json({ access_token: 't', refresh_token: 'r', token_type: 'bearer' }) })
    const onSignedIn = vi.fn()
    withApi(api, <Login onSignedIn={onSignedIn} />)
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.test')
    await userEvent.type(screen.getByLabelText('Password'), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(onSignedIn).toHaveBeenCalled())
  })

  it('shows the server message on failure', async () => {
    const { api } = client({ 'POST /auth/login': () => json({ status: 401, title: 'x', detail: 'Wrong email or password.' }, 401) })
    withApi(api, <Login onSignedIn={vi.fn()} />)
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.test')
    await userEvent.type(screen.getByLabelText('Password'), 'bad')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong email or password.')
  })
})

describe('Documents', () => {
  it('lists documents with their status and links to review', async () => {
    const { api } = client({ 'GET /documents?limit=50&offset=0': () => json([documentOut({ status: 'completed' })]) })
    withApi(api, <Documents />)
    const link = await screen.findByRole('link', { name: 'receipt.pdf' })
    expect(link).toHaveAttribute('href', '#/documents/doc-1')
    expect(screen.getByTestId('status-doc-1')).toHaveTextContent('completed')
  })

  it('uploads a batch and shows per-file results, including rejections', async () => {
    const { api } = client({
      'GET /documents?limit=50&offset=0': () => json([]),
      'POST /documents/batch': () => json([
        { filename: 'a.pdf', document: documentOut({ filename: 'a.pdf' }), error: null, code: null },
        { filename: null, document: null, error: 'Only PDF, JPEG and PNG files are accepted.', code: 'unsupported_type' },
      ]),
    })
    withApi(api, <Documents />)
    await userEvent.upload(screen.getByLabelText('Upload documents'), [new File(['%PDF'], 'a.pdf', { type: 'application/pdf' }), new File(['MZ'], 'b.pdf', { type: 'application/pdf' })])
    const results = await screen.findByRole('list', { name: 'Upload results' })
    expect(within(results).getByText('a.pdf: queued')).toBeInTheDocument()
    expect(within(results).getByText(/Only PDF, JPEG and PNG/)).toBeInTheDocument()
  })

  it('says when a single upload was a duplicate', async () => {
    const { api } = client({
      'GET /documents?limit=50&offset=0': () => json([]),
      'POST /documents': () => json(documentOut({ duplicate: true })),
    })
    withApi(api, <Documents />)
    await userEvent.upload(screen.getByLabelText('Upload documents'), new File(['%PDF'], 'receipt.pdf', { type: 'application/pdf' }))
    expect(await screen.findByText('receipt.pdf: already uploaded')).toBeInTheDocument()
  })

  it('polls unfinished documents and shows the job error code', async () => {
    let calls = 0
    const { api } = client({
      'GET /documents?limit=50&offset=0': () => json([documentOut({ status: 'parsing' })]),
      'GET /documents/doc-1': () => json(documentOut({ status: calls++ ? 'failed' : 'extracting' })),
      'GET /jobs/job-1': () => json({ id: 'job-1', document_id: 'doc-1', state: 'failed', attempts: 4,
        error_code: 'llm_unavailable', error_detail: 'x', dead_lettered: true }),
    })
    withApi(api, <Documents pollMs={20} />)
    await waitFor(() => expect(screen.getByTestId('status-doc-1')).toHaveTextContent('llm_unavailable'), { timeout: 2000 })
  })
})

describe('Review', () => {
  const fields = [
    field(),
    field({ id: 'f-sub', name: 'subtotal', value_raw: '9.000', risk_score: 0.05, decision: 'auto_accepted',
      evidence: [{ page: 1, text: '9.000', bbox: [10, 20, 60, 30], coordinate_system: 'pdf_points_top_left', confidence: null }] }),
  ]

  it('draws one evidence box per field and highlights the selected field', async () => {
    const { api } = client({ 'GET /documents/doc-1/fields': () => json(documentFields(fields)), 'GET /documents/doc-1/pages/1/image': image })
    withApi(api, <Review documentId="doc-1" canReview />)
    await screen.findByRole('img', { name: 'Page 1' })
    const boxes = screen.getAllByTestId('evidence-box')
    expect(boxes).toHaveLength(2)
    // 400-point page drawn 560 px wide: scale 1.4.
    const total = boxes.find((b) => b.getAttribute('data-field') === 'total_amount')!
    expect(total.getAttribute('x')).toBe('140')
    await userEvent.click(screen.getByRole('button', { name: /total amount/ }))
    expect(screen.getByTestId('field-total_amount')).toHaveAttribute('aria-selected', 'true')
  })

  it('approves a field and shows the new decision', async () => {
    const { api, calls } = client({
      'GET /documents/doc-1/fields': () => json(documentFields(fields)),
      'GET /documents/doc-1/pages/1/image': image,
      'POST /fields/f-total/review': () => json(field({ decision: 'approved', final_value: '10.000' })),
    })
    withApi(api, <Review documentId="doc-1" canReview />)
    const row = await screen.findByTestId('field-total_amount')
    await userEvent.click(within(row).getByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(row).toHaveTextContent('Approved'))
    expect(calls.at(-1)?.body).toEqual({ action: 'approve' })
  })

  it('sends a correction and shows the final value', async () => {
    const { api, calls } = client({
      'GET /documents/doc-1/fields': () => json(documentFields(fields)),
      'GET /documents/doc-1/pages/1/image': image,
      'POST /fields/f-total/review': () => json(field({ decision: 'corrected', final_value: '12.500' })),
    })
    withApi(api, <Review documentId="doc-1" canReview />)
    const row = await screen.findByTestId('field-total_amount')
    await userEvent.click(within(row).getByRole('button', { name: 'Correct' }))
    const input = within(row).getByLabelText('Corrected value')
    await userEvent.clear(input)
    await userEvent.type(input, '12.500')
    await userEvent.click(within(row).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(row).toHaveTextContent('final 12.500'))
    expect(calls.at(-1)?.body).toEqual({ action: 'correct', value: '12.500' })
  })

  it('refuses an empty correction without calling the API', async () => {
    const { api, calls } = client({ 'GET /documents/doc-1/fields': () => json(documentFields(fields)), 'GET /documents/doc-1/pages/1/image': image })
    withApi(api, <Review documentId="doc-1" canReview />)
    const row = await screen.findByTestId('field-total_amount')
    await userEvent.click(within(row).getByRole('button', { name: 'Correct' }))
    await userEvent.clear(within(row).getByLabelText('Corrected value'))
    await userEvent.click(within(row).getByRole('button', { name: 'Save' }))
    expect(within(row).getByRole('alert')).toHaveTextContent('Enter the corrected value.')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
  })

  it('shows a server rejection of a correction', async () => {
    const { api } = client({
      'GET /documents/doc-1/fields': () => json(documentFields(fields)),
      'GET /documents/doc-1/pages/1/image': image,
      'POST /fields/f-total/review': () => json({ status: 422, title: 'x', detail: 'The corrected value does not parse for this field.', code: 'value_invalid' }, 422),
    })
    withApi(api, <Review documentId="doc-1" canReview />)
    const row = await screen.findByTestId('field-total_amount')
    await userEvent.click(within(row).getByRole('button', { name: 'Correct' }))
    await userEvent.type(within(row).getByLabelText('Corrected value'), 'x')
    await userEvent.click(within(row).getByRole('button', { name: 'Save' }))
    expect(await within(row).findByRole('alert')).toHaveTextContent('does not parse')
  })

  it('hides review actions from viewers', async () => {
    const { api } = client({ 'GET /documents/doc-1/fields': () => json(documentFields(fields)), 'GET /documents/doc-1/pages/1/image': image })
    withApi(api, <Review documentId="doc-1" canReview={false} />)
    await screen.findByTestId('field-total_amount')
    expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull()
  })

  it('filters to fields that need review', async () => {
    const { api } = client({ 'GET /documents/doc-1/fields': () => json(documentFields(fields)), 'GET /documents/doc-1/pages/1/image': image })
    withApi(api, <Review documentId="doc-1" canReview />)
    await screen.findByTestId('field-subtotal')
    expect(screen.getByText('1 to review')).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Only fields to review'))
    expect(screen.queryByTestId('field-subtotal')).toBeNull()
    expect(screen.getByTestId('field-total_amount')).toBeInTheDocument()
  })

  it('exports JSON and CSV through the API', async () => {
    const { api, calls } = client({
      'GET /documents/doc-1/fields': () => json(documentFields(fields)),
      'GET /documents/doc-1/pages/1/image': image,
      'GET /documents/doc-1/export?format=json': () => json({}),
      'GET /documents/doc-1/export?format=csv': () => new Response('a,b'),
    })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    withApi(api, <Review documentId="doc-1" canReview />)
    await userEvent.click(await screen.findByRole('button', { name: 'Export JSON' }))
    await userEvent.click(screen.getByRole('button', { name: 'Export CSV' }))
    await waitFor(() => expect(click).toHaveBeenCalledTimes(2))
    expect(calls.filter((c) => c.path.includes('/export')).map((c) => c.path)).toEqual([
      '/documents/doc-1/export?format=json', '/documents/doc-1/export?format=csv',
    ])
  })

  it('explains when the document is still processing', async () => {
    const { api } = client({ 'GET /documents/doc-1/fields': () => json({ status: 409, title: 'Not ready', code: 'not_ready' }, 409) })
    withApi(api, <Review documentId="doc-1" canReview />)
    expect(await screen.findByRole('alert')).toHaveTextContent('still being processed')
  })

  it('says when values come from a rules fallback', async () => {
    const degraded = { ...documentFields(fields), degraded_reason: 'llm_unavailable: provider down' }
    const { api } = client({ 'GET /documents/doc-1/fields': () => json(degraded), 'GET /documents/doc-1/pages/1/image': image })
    withApi(api, <Review documentId="doc-1" canReview />)
    expect(await screen.findByRole('status')).toHaveTextContent('llm_unavailable')
  })
})

describe('Queue', () => {
  it('shows pending fields in the order the API returns, with links', async () => {
    const { api } = client({
      'GET /review/queue?limit=200': () => json([
        { field_id: 'a', document_id: 'd1', filename: 'one.pdf', name: 'tax_amount', value_raw: '1', risk_score: 0.9, created_at: 'x' },
        { field_id: 'b', document_id: 'd2', filename: 'two.pdf', name: 'line_items[0].amount', value_raw: null, risk_score: 0.4, created_at: 'x' },
      ]),
    })
    withApi(api, <Queue />)
    const rows = await screen.findAllByTestId('queue-row')
    expect(rows.map((row) => row.textContent)).toEqual(['0.90tax amount1one.pdf', '0.40Row 1: amount—two.pdf'])
    expect(within(rows[1]).getByRole('link')).toHaveAttribute('href', '#/documents/d2')
  })

  it('says when nothing waits', async () => {
    const { api } = client({ 'GET /review/queue?limit=200': () => json([]) })
    withApi(api, <Queue />)
    expect(await screen.findByText('Nothing waits for review.')).toBeInTheDocument()
  })
})

describe('Report', () => {
  const unavailable = (source: string) => ({ available: false, source })
  const comparison = {
    metrics_version: '1.1.1', split: 'validation', note: 'Development only.',
    systems: [{
      system: 'S1', source: 's', model: null, prompt: null, n_documents: 100,
      fields: { total_amount: { f1: 0.83, f1_ci95: [0.755, 0.899], precision: 0.867, recall: 0.796, false_fill_rate: 0 } },
      line_items_row_level: { f1: 0.377, f1_ci95: [0.296, 0.456] },
      failures: { failed_extractions: 0, pass_fallbacks: 0 },
    }],
  }

  it('shows committed results with intervals and flags files not produced yet', async () => {
    const { api } = client({
      'GET /evaluation/report': () => json({
        test_comparison: unavailable('t'), s5_test: unavailable('f'),
        validation_comparison: { available: true, source: 'evals/results/dev/c.json', data: comparison },
        prompt_round: unavailable('p'), s1_test: unavailable('s'),
        s5_s1_validation: unavailable('a'), s5_s4h_validation: unavailable('b'), note: 'Validation only.',
      }),
    })
    withApi(api, <Report />)
    const row = await screen.findByTestId('validation-S1')
    expect(row).toHaveTextContent('0.830')
    expect(row).toHaveTextContent('[0.755, 0.899]')
    expect(row).toHaveTextContent('rules')
    expect(screen.getByTestId('source-s5_s1_validation')).toHaveTextContent('not produced yet')
    expect(screen.getByText('Validation only.')).toBeInTheDocument()
  })

  it('shows the final test table before the validation table', async () => {
    const test = { ...comparison, split: 'test', note: 'Final test read.' }
    const { api } = client({
      'GET /evaluation/report': () => json({
        test_comparison: { available: true, source: 'evals/results/final/t.json', data: test },
        s5_test: { available: true, source: 'evals/results/final/s5.json', data: {} },
        validation_comparison: { available: true, source: 'evals/results/dev/c.json', data: comparison },
        prompt_round: unavailable('p'), s1_test: unavailable('s'),
        s5_s1_validation: unavailable('a'), s5_s4h_validation: unavailable('b'), note: 'Final read done.',
      }),
    })
    withApi(api, <Report />)
    const testRow = await screen.findByTestId('test-S1')
    const validationRow = screen.getByTestId('validation-S1')
    expect(testRow.compareDocumentPosition(validationRow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByTestId('source-s5_test')).not.toHaveTextContent('not produced yet')
  })
})

describe('App', () => {
  it('asks for sign-in when there is no session', () => {
    const { api } = client({})
    render(<App client={api} />)
    expect(screen.getByRole('form', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('routes by hash once signed in', async () => {
    tokenStore.set(tokenWithRole('reviewer'))
    window.location.hash = '#/queue'
    const { api } = client({ 'GET /review/queue?limit=200': () => json([]) })
    render(<App client={api} />)
    expect(await screen.findByRole('heading', { name: 'Review queue' })).toBeInTheDocument()
  })
})
