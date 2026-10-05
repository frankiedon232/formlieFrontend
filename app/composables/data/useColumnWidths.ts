/**
 * Resizable columns for a DataView table (the database explorer only, owner 2026-10-05): drag the
 * line between two headers, double-click it to fit the column to its content, or focus it and use
 * ← / → (Shift: bigger steps). Widths are remembered per list on this browser (a view preference,
 * like the column order). The table switches to a fixed layout so the widths hold.
 */
import type { VNode } from 'vue'

/** The part of a table header this needs (TanStack's header, typed by shape). */
interface ResizableHeader {
  getSize: () => number
  getResizeHandler: () => (event: unknown) => void
  column: { getIsResizing: () => boolean }
}

export function useColumnWidths(id: MaybeRefOrGetter<string>, root: Ref<HTMLElement | null>) {
  const { t } = useI18n()
  const widths = useLocalStorage<Record<string, number>>(() => `formalie:widths:${toValue(id)}`, {})
  const clamp = (value: number) => Math.round(Math.min(COLUMN_WIDTH.max, Math.max(COLUMN_WIDTH.min, value)))
  const set = (key: string, value: number) => (widths.value = { ...widths.value, [key]: clamp(value) })
  const sizeOf = (key: string, start = COLUMN_WIDTH.start) => widths.value[key] ?? start

  /** The widest cell of a column (its full content, not the clipped one). */
  function fit(key: string, head: HTMLTableCellElement | null) {
    if (!head) return
    const index = head.cellIndex + 1
    const cells = [...(root.value?.querySelectorAll(`tbody tr td:nth-child(${index})`) ?? [])] as HTMLElement[]
    const widest = Math.max(head.scrollWidth, ...cells.map(cell => [...cell.children].reduce((sum, child) => Math.max(sum, (child as HTMLElement).scrollWidth), 0) + 28))
    set(key, widest)
  }

  /** The header's content with a resize line on its end edge. */
  function withHandle(key: string, label: string, header: ResizableHeader, content: VNode | string): VNode {
    const handle = h('span', {
      role: 'separator',
      tabindex: 0,
      'aria-orientation': 'vertical',
      'aria-label': t('dataView.resizeColumn', { name: label }),
      'aria-valuenow': header.getSize(),
      'aria-valuemin': COLUMN_WIDTH.min,
      'aria-valuemax': COLUMN_WIDTH.max,
      title: t('dataView.resizeHint'),
      class: [
        'group/handle absolute inset-y-0 -end-1.5 z-10 flex w-3 cursor-col-resize touch-none justify-center select-none focus-visible:outline-none',
        "after:my-1.5 after:w-px after:rounded-full after:bg-(--ui-border-accented) after:transition-colors",
        'hover:after:w-0.5 hover:after:bg-(--ui-border-inverted) focus-visible:after:w-0.5 focus-visible:after:bg-(--ui-border-inverted)',
        header.column.getIsResizing() ? 'after:w-0.5 after:bg-(--ui-border-inverted)' : '',
      ].join(' '),
      onMousedown: header.getResizeHandler(),
      onTouchstart: header.getResizeHandler(),
      onClick: (event: Event) => event.stopPropagation(),
      onDblclick: (event: Event) => {
        event.stopPropagation()
        fit(key, (event.target as HTMLElement).closest('th'))
      },
      onKeydown: (event: KeyboardEvent) => {
        const step = event.shiftKey ? COLUMN_WIDTH.step * 4 : COLUMN_WIDTH.step
        const direction = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
        if (!direction) return
        event.preventDefault()
        // Right-to-left layouts: the arrow follows what you see.
        const rtl = getComputedStyle(event.target as Element).direction === 'rtl'
        set(key, header.getSize() + step * direction * (rtl ? -1 : 1))
      },
    })
    return h('div', { class: 'flex min-w-0 items-center pe-2' }, [h('div', { class: 'min-w-0 truncate' }, [content]), handle])
  }

  const reset = () => (widths.value = {})
  const total = (columns: { key: string; width?: number }[]) => columns.reduce((sum, column) => sum + sizeOf(column.key, column.width), 0)

  return { widths, sizeOf, withHandle, fit, reset, total }
}

/** Column widths in pixels: first width, the narrowest and widest, the arrow-key step. */
export const COLUMN_WIDTH = { start: 180, min: 64, max: 1000, step: 16 }
