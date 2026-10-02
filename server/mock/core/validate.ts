import type { z } from 'zod'
import { MockError } from './respond'

/** zod parse → FRM-GEN-1002 with per-field details (what UForm shows inline). */
export function parseBody<T extends z.ZodType>(schema: T, body: unknown): z.infer<T> {
  const result = schema.safeParse(body)
  if (result.success) return result.data
  throw new MockError(
    'FRM-GEN-1002',
    result.error.issues.map(issue => ({ field: issue.path.join('.'), message: issue.message })),
  )
}
