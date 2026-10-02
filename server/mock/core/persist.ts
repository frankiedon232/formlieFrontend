/**
 * Dev-only persistence for the mock: a reload of the mock code (every edit under server/)
 * restarts the server worker and would wipe in-memory sessions, signing everyone out.
 * Small JSON files under `.data/mock/` (gitignored) keep them across reloads.
 * The real backend keeps sessions in Postgres / Redis.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const DIR = join(process.cwd(), '.data', 'mock')
const timers = new Map<string, ReturnType<typeof setTimeout>>()

export function loadPersisted<T>(name: string, fallback: T): T {
  try {
    const file = join(DIR, `${name}.json`)
    return existsSync(file) ? (JSON.parse(readFileSync(file, 'utf8')) as T) : fallback
  } catch {
    return fallback
  }
}

/** Debounced write (many token rotations per second must not hammer the disk). */
export function savePersisted(name: string, snapshot: () => unknown) {
  clearTimeout(timers.get(name))
  timers.set(
    name,
    setTimeout(() => {
      try {
        mkdirSync(DIR, { recursive: true })
        writeFileSync(join(DIR, `${name}.json`), JSON.stringify(snapshot()))
      } catch (error) {
        console.warn(`[mock] could not save ${name}:`, error)
      }
    }, 200),
  )
}
