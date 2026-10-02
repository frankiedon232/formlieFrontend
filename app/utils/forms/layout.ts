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
