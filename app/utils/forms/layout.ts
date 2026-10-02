/**
 * Field widths on the 12-column grid, as **container** queries (Tailwind `@container`): the form
 * decides by its own width, not the window — so the phone preview (390 px) stacks every field
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
  return `${Math.min(longest, 26) + 1}ch`
}
