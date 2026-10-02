/**
 * The design's segmented control (Table / Kanban / Timeline, Daily / Weekly / Monthly,
 * Week 1 / Week 2 in docs/design): light grey track, the active option white with a hairline
 * border and a soft shadow, inactive options muted. Use on every <UTabs> that switches a view:
 *
 *   <UTabs :items="…" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" />
 */
export const SEGMENTED_UI = {
  list: 'rounded-lg bg-elevated',
  indicator: 'rounded-md bg-default shadow-xs ring ring-default',
  trigger: 'px-2.5 text-muted hover:text-default data-[state=active]:text-highlighted',
} as const
