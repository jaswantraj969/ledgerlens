import { useEffect, useState } from 'react'
import { errorMessage, useApi } from '../api/context'
import { comparison as comparisonSchema, type Comparison, type Report as ReportData } from '../api/schemas'
import { formatInterval, formatRate } from '../lib/format'

const FIELDS: [string, string][] = [
  ['total_amount', 'Total'],
  ['subtotal', 'Subtotal'],
  ['tax_amount', 'Tax'],
]

const BLOCK_TITLES: Record<string, string> = {
  test_comparison: 'CORD test, final read, all systems',
  s5_test: 'S5 on CORD test (automation and achieved precision)',
  validation_comparison: 'CORD validation, all systems',
  prompt_round: 'Prompt round (train subset)',
  s1_test: 'S1 on CORD test',
  s5_s1_validation: 'S5 on S1, validation',
  s5_s4h_validation: 'S5 on S4h, validation',
}

/** Shows committed results only. Every block names its source file; missing ones say so. */
export function Report() {
  const api = useApi()
  const [report, setReport] = useState<ReportData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.report().then(setReport).catch((failure) => setError(errorMessage(failure)))
  }, [api])

  if (error) return <p role="alert" className="text-red-700">{error}</p>
  if (!report) return <p>Loading…</p>
  const test = report.test_comparison.available
    ? comparisonSchema.safeParse(report.test_comparison.data)
    : null
  const parsed = report.validation_comparison.available
    ? comparisonSchema.safeParse(report.validation_comparison.data)
    : null

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold">Evaluation report</h2>
      <p className="text-sm">{report.note}</p>
      {test?.success && <ComparisonTable comparison={test.data} />}
      {test && !test.success && <p role="alert">The test comparison file has an unexpected format.</p>}
      {parsed?.success && <ComparisonTable comparison={parsed.data} />}
      {parsed && !parsed.success && (
        <p role="alert">The validation comparison file has an unexpected format.</p>
      )}
      <h3 className="font-semibold">Sources</h3>
      <ul className="text-sm">
        {Object.entries(BLOCK_TITLES).map(([key, title]) => {
          const block = report[key as keyof Omit<ReportData, 'note'>]
          return (
            <li key={key} data-testid={`source-${key}`}>
              {title}: <code>{block.source}</code>{' '}
              {block.available ? '' : <strong>not produced yet</strong>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function ComparisonTable({ comparison }: { comparison: Comparison }) {
  return (
    <div>
      <h3 className="font-semibold">
        CORD {comparison.split}, metrics {comparison.metrics_version}: F1 [95% CI]
      </h3>
      <p className="text-sm text-slate-600">{comparison.note}</p>
      <table className="mt-2 w-full text-left text-sm">
        <thead>
          <tr>
            <th>System</th><th>Model / prompt</th>
            {FIELDS.map(([, label]) => <th key={label}>{label}</th>)}
            <th>Rows</th><th>Failed</th>
          </tr>
        </thead>
        <tbody>
          {comparison.systems.map((system) => (
            <tr key={system.system} className="border-t" data-testid={`${comparison.split}-${system.system}`}>
              <td>{system.system}</td>
              <td>{system.model ? `${system.model} ${system.prompt ?? ''}` : 'rules'}</td>
              {FIELDS.map(([key]) => (
                <td key={key}>
                  {formatRate(system.fields[key]?.f1)}{' '}
                  <span className="text-xs text-slate-500">{formatInterval(system.fields[key]?.f1_ci95)}</span>
                </td>
              ))}
              <td>
                {formatRate(system.line_items_row_level.f1)}{' '}
                <span className="text-xs text-slate-500">{formatInterval(system.line_items_row_level.f1_ci95)}</span>
              </td>
              <td>{system.failures.failed_extractions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
