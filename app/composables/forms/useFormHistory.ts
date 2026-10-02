/**
 * Undo / redo for the builder: JSON snapshots of the schema (small, safe, simple). Rapid edits
 * with the same `group` (typing a label) collapse into one step. Capped at 100 steps.
 */
const LIMIT = 100
const GROUP_WINDOW_MS = 800

export function useFormHistory<T>(read: () => T, write: (value: T) => void) {
  const past = shallowRef<string[]>([])
  const future = shallowRef<string[]>([])
  let lastGroup: string | null = null
  let lastAt = 0

  /** Call before a change. Same `group` within 800 ms extends the previous step. */
  function record(group?: string) {
    const now = Date.now()
    if (group && group === lastGroup && now - lastAt < GROUP_WINDOW_MS) {
      lastAt = now
      return
    }
    lastGroup = group ?? null
    lastAt = now
    past.value = [...past.value.slice(-(LIMIT - 1)), JSON.stringify(read())]
    future.value = []
  }

  function undo(): boolean {
    const previous = past.value.at(-1)
    if (previous === undefined) return false
    future.value = [JSON.stringify(read()), ...future.value]
    past.value = past.value.slice(0, -1)
    lastGroup = null
    write(JSON.parse(previous) as T)
    return true
  }

  function redo(): boolean {
    const next = future.value[0]
    if (next === undefined) return false
    past.value = [...past.value, JSON.stringify(read())]
    future.value = future.value.slice(1)
    lastGroup = null
    write(JSON.parse(next) as T)
    return true
  }

  function reset() {
    past.value = []
    future.value = []
    lastGroup = null
  }

  return {
    record,
    undo,
    redo,
    reset,
    canUndo: computed(() => past.value.length > 0),
    canRedo: computed(() => future.value.length > 0),
  }
}
