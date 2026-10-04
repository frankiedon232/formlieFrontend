/**
 * Field widths on the 12-column grid, as **container** queries (Tailwind `@container`): the form
 * decides by its own width, not the window, so the phone preview (390 px) stacks every field
 * on its own row even on a desktop screen, and a form embedded in a narrow column does too.
 * Literal class names so Tailwind finds them.
 */
export const FIELD_SPAN: Record<number, string> = {
  12: '@md:col-span-12',
  9: '@md:col-span-9',
  8: '@md:col-span-8',
  6: '@md:col-span-6',
  4: '@md:col-span-4',
  3: '@md:col-span-3',
}

/** Smaller corner radius for form controls than the portal chrome (owner: "just small"). */
export const FORM_RADIUS = '[--ui-radius:0.25rem]'

/**
 * "Beside the field": one label width for the whole form, sized to its longest label (in `ch`,
 * plus room for the * and the info icon), capped so long labels wrap instead of squeezing the
 * input. Set as `--form-label-w` on the form; labels are end-aligned so they hug their input and
 * every input starts on the same line.
 */
export function labelColumnWidth(fields: { type: string; label?: string; required?: boolean; help?: string }[]) {
  const longest = fields
    .filter(f => !['hidden', 'section', 'paragraph', 'divider', 'image'].includes(f.type))
    .reduce((max, f) => Math.max(max, (f.label?.trim().length ?? 0) + (f.required ? 2 : 0) + (f.help ? 3 : 0)), 8)
  return `${Math.min(longest, 22) + 1}ch`
}

/**
 * Drag and drop placeholder: SortableJS marks the spot where the field will land with
 * `ghost-class="drop-ghost"`; the drop area (canvas) styles it as a dashed, tinted box with a
 * label from `--drop-label` ("Drop here, new row" / "… beside"). Literal classes for Tailwind.
 */
export const DROP_GHOST = 'drop-ghost'
export const DROP_ZONE = [
  '[&_.drop-ghost]:relative [&_.drop-ghost]:min-h-14 [&_.drop-ghost]:overflow-hidden [&_.drop-ghost]:rounded-lg',
  '[&_.drop-ghost]:border-2 [&_.drop-ghost]:border-dashed [&_.drop-ghost]:border-(--ui-border-inverted)',
  '[&_.drop-ghost]:bg-elevated [&_.drop-ghost]:opacity-100 [&_.drop-ghost]:shadow-none',
  '[&_.drop-ghost]:text-transparent [&_.drop-ghost>*]:invisible',
  '[&_.drop-ghost]:after:absolute [&_.drop-ghost]:after:inset-0 [&_.drop-ghost]:after:flex [&_.drop-ghost]:after:items-center',
  '[&_.drop-ghost]:after:justify-center [&_.drop-ghost]:after:gap-1 [&_.drop-ghost]:after:text-xs [&_.drop-ghost]:after:font-medium',
  '[&_.drop-ghost]:after:text-highlighted [&_.drop-ghost]:after:content-(--drop-label)',
].join(' ')
/** In a row (next to other fields) the placeholder takes half the row on wider forms. */
export const DROP_ZONE_ROW = '[&>.drop-ghost]:col-span-12 @md:[&>.drop-ghost]:col-span-6'

/** Rich text content look (editor, read-only view, paragraph block): standard line height, small gaps. */
export const RICH_TEXT_BASE =
  'text-sm leading-5 *:my-0.5 sm:px-0 [&_p]:leading-5 [&_li]:leading-5 [&_pre]:my-1.5 px-0 py-0'
