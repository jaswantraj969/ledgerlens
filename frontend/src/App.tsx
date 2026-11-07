import { useMemo, useState } from 'react'
import { ApiClient, tokenStore } from './api/client'
import { ApiContext } from './api/context'
import { Documents } from './components/Documents'
import { Login } from './components/Login'
import { Queue } from './components/Queue'
import { Report } from './components/Report'
import { Review } from './components/Review'
import { roleFromToken } from './lib/auth'
import { hrefFor, useRoute } from './router'

export default function App({ client }: { client?: ApiClient }) {
  const [token, setToken] = useState(() => tokenStore.get())
  const api = useMemo(() => client ?? new ApiClient('/api', undefined, () => setToken(null)), [client])
  const route = useRoute()
  const role = roleFromToken(token)

  return (
    <ApiContext.Provider value={api}>
      <main className="mx-auto max-w-6xl p-6">
        <header className="mb-6 flex items-center gap-6">
          <h1 className="text-2xl font-semibold">LedgerLens</h1>
          {token && (
            <nav aria-label="Main" className="flex gap-4 text-sm">
              <a href={hrefFor({ page: 'documents' })}>Documents</a>
              <a href={hrefFor({ page: 'queue' })}>Review queue</a>
              <a href={hrefFor({ page: 'report' })}>Evaluation</a>
              <button type="button" onClick={() => { api.logout(); setToken(null) }}>Sign out</button>
            </nav>
          )}
        </header>
        {!token ? (
          <Login onSignedIn={() => setToken(tokenStore.get())} />
        ) : route.page === 'review' ? (
          <Review documentId={route.documentId} canReview={role === 'admin' || role === 'reviewer'} />
        ) : route.page === 'queue' ? (
          <Queue />
        ) : route.page === 'report' ? (
          <Report />
        ) : (
          <Documents />
        )}
      </main>
    </ApiContext.Provider>
  )
}
