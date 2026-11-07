import { useEffect, useState } from 'react'

export type Route =
  | { page: 'documents' }
  | { page: 'review'; documentId: string }
  | { page: 'queue' }
  | { page: 'report' }

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#\/?/, '')
  const [first, second] = path.split('/')
  if (first === 'documents' && second) return { page: 'review', documentId: decodeURIComponent(second) }
  if (first === 'queue') return { page: 'queue' }
  if (first === 'report') return { page: 'report' }
  return { page: 'documents' }
}

export function hrefFor(route: Route): string {
  switch (route.page) {
    case 'review':
      return `#/documents/${encodeURIComponent(route.documentId)}`
    case 'queue':
      return '#/queue'
    case 'report':
      return '#/report'
    default:
      return '#/documents'
  }
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash))
  useEffect(() => {
    const update = () => setRoute(parseRoute(window.location.hash))
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  return route
}
