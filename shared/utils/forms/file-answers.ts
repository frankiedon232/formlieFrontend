/**
 * File question answers (F10 M2): a list of `FileAnswer`, the files themselves are in storage.
 * Older answers (or anything hand-made) that aren't in this shape are treated as no files.
 */
import type { FileAnswer } from '../../types/public'

export const FILE_FIELD_TYPES = ['file_upload', 'image_upload'] as const

export const isFileField = (type: string) => (FILE_FIELD_TYPES as readonly string[]).includes(type)

export function isFileAnswer(value: unknown): value is FileAnswer {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return typeof item.id === 'string' && typeof item.name === 'string' && typeof item.size === 'number' && typeof item.type === 'string'
}

/** The file answers in a stored value (empty when there are none). */
export const fileAnswers = (value: unknown): FileAnswer[] => (Array.isArray(value) ? value.filter(isFileAnswer) : [])

/** Largest file a respondent may upload, whatever a question allows (bytes). */
export const MAX_RESPONDENT_FILE_BYTES = 25 * 1024 * 1024

/** A question's own size limit in bytes (its "max MB", default 10, never above the platform limit). */
export function maxFileBytes(props: Record<string, unknown> | undefined): number {
  const mb = Number(props?.max_mb ?? 10)
  return Math.min(MAX_RESPONDENT_FILE_BYTES, (Number.isFinite(mb) && mb > 0 ? mb : 10) * 1024 * 1024)
}
