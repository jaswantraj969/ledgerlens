import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const FIXTURE = resolve(dirname(fileURLToPath(import.meta.url)), '.fixtures', 'invoice.pdf')

/** Generate a synthetic invoice with the project's own generator. Nothing real is used. */
export default function globalSetup(): void {
  mkdirSync(dirname(FIXTURE), { recursive: true })
  const root = resolve(dirname(FIXTURE), '..', '..', '..')
  const code =
    'import sys; from evals.synthetic.generate import generate_invoice; ' +
    "open(sys.argv[1], 'wb').write(generate_invoice(31, layout='classic').pdf)"
  execFileSync('uv', ['run', '--project', 'backend', '--no-sync', 'python', '-c', code, FIXTURE], {
    cwd: root,
    stdio: 'inherit',
  })
}
