import type { PageOut } from '../api/schemas'

export interface Box {
  left: number
  top: number
  width: number
  height: number
}

/**
 * Map a token box [x0, y0, x1, y1] (top-left origin, in the page's own units: PDF points or
 * image pixels) onto a displayed image of the given pixel size. Returns null for a box that
 * is missing, inverted or outside the page, so nothing is drawn where the evidence is unclear.
 */
export function scaleBox(
  bbox: readonly number[] | null,
  page: Pick<PageOut, 'width' | 'height'>,
  displayWidth: number,
  displayHeight: number,
): Box | null {
  if (!bbox || bbox.length !== 4 || page.width <= 0 || page.height <= 0) return null
  const [x0, y0, x1, y1] = bbox
  if (x1 <= x0 || y1 <= y0 || x0 < 0 || y0 < 0 || x1 > page.width || y1 > page.height) return null
  const sx = displayWidth / page.width
  const sy = displayHeight / page.height
  return { left: x0 * sx, top: y0 * sy, width: (x1 - x0) * sx, height: (y1 - y0) * sy }
}
