import { useEffect, useState } from 'react'
import { errorMessage, useApi } from '../api/context'
import type { FieldOut, PageOut } from '../api/schemas'
import { scaleBox } from '../lib/geometry'

export const DISPLAY_WIDTH = 560

interface Props {
  documentId: string
  page: PageOut
  fields: FieldOut[]
  selectedId: string | null
  onSelect: (fieldId: string) => void
}

/** The page image with evidence boxes drawn over it, in the page's own coordinate system. */
export function PageViewer({ documentId, page, fields, selectedId, onSelect }: Props) {
  const api = useApi()
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const displayHeight = (DISPLAY_WIDTH * page.height) / page.width

  useEffect(() => {
    let url: string | null = null
    let alive = true
    api
      .pageImage(documentId, page.number)
      .then((blob) => {
        if (!alive) return
        url = URL.createObjectURL(blob)
        setSrc(url)
      })
      .catch((failure) => alive && setError(errorMessage(failure)))
    return () => {
      alive = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [api, documentId, page.number])

  const boxes = fields.flatMap((field) =>
    field.evidence
      .filter((evidence) => evidence.page === page.number)
      .map((evidence, index) => ({
        key: `${field.id}-${index}`,
        field,
        box: scaleBox(evidence.bbox, page, DISPLAY_WIDTH, displayHeight),
      }))
      .filter((item) => item.box !== null),
  )

  return (
    <figure className="relative" style={{ width: DISPLAY_WIDTH, height: displayHeight }}>
      {src ? (
        <img src={src} alt={`Page ${page.number}`} width={DISPLAY_WIDTH} height={displayHeight} />
      ) : (
        <div className="flex h-full items-center justify-center bg-slate-100 text-sm">
          {error ?? 'Loading page…'}
        </div>
      )}
      <svg className="absolute inset-0" width={DISPLAY_WIDTH} height={displayHeight}
        aria-label={`Evidence on page ${page.number}`}>
        {boxes.map(({ key, field, box }) => (
          <rect key={key} data-testid="evidence-box" data-field={field.name}
            x={box!.left} y={box!.top} width={box!.width} height={box!.height}
            className={field.id === selectedId ? 'fill-amber-300/40 stroke-amber-600' : 'fill-sky-300/20 stroke-sky-600'}
            strokeWidth={field.id === selectedId ? 2 : 1}
            onClick={() => onSelect(field.id)} />
        ))}
      </svg>
    </figure>
  )
}
