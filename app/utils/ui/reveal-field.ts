/**
 * Bring a form field into view and focus it (owner 2026-10-04: a flagged field at the top of a
 * scrolling panel must not stay hidden). Scrolls the nearest scrolling box that holds it, since
 * scrollIntoView doesn't move nested scroll areas reliably, and jumps when a browser ignores
 * smooth scrolling.
 */
export function revealField(id: string) {
  const field = document.getElementById(id)
  if (!field) return
  let box = field.parentElement
  while (box && !(box.scrollHeight > box.clientHeight && /auto|scroll/.test(getComputedStyle(box).overflowY))) box = box.parentElement
  field.focus({ preventScroll: true })
  if (!box) return field.scrollIntoView({ block: 'center' })
  const top = Math.max(0, box.scrollTop + field.getBoundingClientRect().top - box.getBoundingClientRect().top - 48)
  box.scrollTo({ top, behavior: 'smooth' })
  const from = box.scrollTop
  setTimeout(() => box && Math.abs(box.scrollTop - top) > 4 && box.scrollTop === from && box.scrollTo({ top }), 350)
}
