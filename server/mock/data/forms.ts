/**
 * Seeded, deterministic mock forms (same data after every restart).
 * Replaced by the FastAPI backend; shapes follow shared/types/forms.ts.
 */
import type { FormFolder, FormOwner, FormStatus, FormSummary } from '#shared/types/forms'

function seeded(seed: number) {
  let state = seed
  return () => {
    state = (state * 1_103_515_245 + 12_345) % 2_147_483_648
    return state / 2_147_483_648
  }
}

const random = seeded(20261002)
const pick = <T>(items: readonly T[]): T => items[Math.floor(random() * items.length)]!

function uuid(): string {
  const hex = () => Math.floor(random() * 16).toString(16)
  const part = (n: number) => Array.from({ length: n }, hex).join('')
  return `${part(8)}-${part(4)}-4${part(3)}-a${part(3)}-${part(12)}`
}

export const MOCK_OWNERS: FormOwner[] = [
  { id: uuid(), name: 'Sofia Martins' },
  { id: uuid(), name: 'Kenji Watanabe' },
  { id: uuid(), name: 'Priya Raman' },
  { id: uuid(), name: 'Alex Novak' },
  { id: uuid(), name: 'Lukas Becker' },
]

export const MOCK_FOLDERS: FormFolder[] = [
  { id: uuid(), name: 'Marketing' },
  { id: uuid(), name: 'HR' },
  { id: uuid(), name: 'Operations' },
  { id: uuid(), name: 'Compliance' },
]

const NAMES = [
  'Customer feedback survey',
  'Event registration',
  'Job application',
  'Employee onboarding',
  'Incident report',
  'Patient intake',
  'NPS quarterly',
  'Contact us',
  'Order form',
  'Supplier KYC',
  'Safety audit checklist',
  'Course evaluation',
  'Volunteer sign-up',
  'Product return request',
  'Lead capture',
  'Exit interview',
  'Training enrolment',
  'Membership renewal',
  'Bug report',
  'Venue booking',
]
const TAGS = ['internal', 'public', 'q4', 'priority', 'pilot', 'hr', 'sales']
const STATUSES: FormStatus[] = ['draft', 'published', 'published', 'published', 'closed', 'archived']

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')

const now = Date.parse('2026-10-02T09:00:00Z')

export const MOCK_FORMS: FormSummary[] = Array.from({ length: 57 }, (_, index) => {
  const base = NAMES[index % NAMES.length]!
  const name = index < NAMES.length ? base : `${base} ${Math.floor(index / NAMES.length) + 1}`
  const status = pick(STATUSES)
  const created = now - Math.floor(random() * 300) * 86_400_000
  const updated = Math.min(
    now,
    created + Math.floor(random() * 60) * 86_400_000 + Math.floor(random() * 86_400_000),
  )
  return {
    id: uuid(),
    name,
    slug: slugify(name),
    status,
    has_unpublished_changes: status === 'published' && random() < 0.3,
    folder: random() < 0.75 ? pick(MOCK_FOLDERS) : null,
    owner: pick(MOCK_OWNERS),
    tags: TAGS.filter(() => random() < 0.2),
    responses_count: status === 'draft' ? 0 : Math.floor(random() * 2400),
    completion_rate: status === 'draft' ? 0 : Math.round(40 + random() * 60),
    created_at: new Date(created).toISOString(),
    updated_at: new Date(updated).toISOString(),
    row_version: 1,
    deleted_at: null,
  }
})
