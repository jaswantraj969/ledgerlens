import { useState, type FormEvent } from 'react'
import { errorMessage, useApi } from '../api/context'

export function Login({ onSignedIn }: { onSignedIn: () => void }) {
  const api = useApi()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.login(email, password)
      onSignedIn()
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-16 max-w-sm space-y-4" aria-label="Sign in">
      <h1 className="text-2xl font-semibold">Sign in to LedgerLens</h1>
      <label className="block">
        <span className="text-sm">Email</span>
        <input className="mt-1 w-full rounded border px-2 py-1" type="email" required
          value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="block">
        <span className="text-sm">Password</span>
        <input className="mt-1 w-full rounded border px-2 py-1" type="password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <button type="submit" disabled={busy}
        className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50">
        {busy ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  )
}
