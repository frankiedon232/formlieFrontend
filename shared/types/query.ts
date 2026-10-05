/**
 * The Query editor (F12 M4): one statement per run, on Formalie's servers through the connection,
 * with a time limit, paged results and a capped count. A statement that changes rows or structure
 * asks for a confirm first (FRM-DEST-1023 with what it will do), and follows the connection's
 * access (Read only: reading only; never Formalie's response tables).
 */
import type { StatementKind } from '#shared/utils/datasources/sql'

export interface QueryRequest {
  sql: string
  /** Values for `:name` parameters (bound by the server, never pasted into the SQL). */
  params?: Record<string, string>
  page?: number
  page_size?: number
  /** The person confirmed a changing statement. */
  confirm?: boolean
}

export interface QueryColumn {
  name: string
  type: string | null
}

export interface QueryResult {
  run_id: string
  kind: StatementKind
  columns: QueryColumn[]
  /** This page of the result, each row as values in column order. */
  rows: unknown[][]
  page: number
  page_size: number
  /** Rows in the result (counted up to 10,000; `capped` above that), null for changes. */
  total: number | null
  capped: boolean
  rows_affected: number | null
  duration_ms: number
  /** A note about the run (e.g. a structure statement in the preview). */
  notice: string | null
}

/** What a changing statement will do (sent with FRM-DEST-1023 before it runs). */
export interface QueryConfirm {
  kind: StatementKind
  tables: string[]
  /** Rows it will touch, when known. */
  estimate: number | null
}

export interface QueryHistoryItem {
  id: string
  sql: string
  kind: StatementKind
  ran_at: string
  duration_ms: number | null
  rows: number | null
  ok: boolean
  error_code: string | null
}
