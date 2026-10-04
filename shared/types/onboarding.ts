/** Onboarding wizard + upload shapes (docs/API-CONTRACT.md → Tenants and onboarding, Uploads). */
import type { StarterTemplateKey } from '../utils/templates/starters'

export const ONBOARDING_STEPS = ['company', 'branding', 'localisation', 'team', 'first_form'] as const
export type OnboardingStep = (typeof ONBOARDING_STEPS)[number]
export type OnboardingStepStatus = 'todo' | 'done' | 'skipped'

export const INDUSTRIES = [
  'professional_services',
  'legal',
  'finance',
  'healthcare',
  'education',
  'government',
  'non_profit',
  'technology',
  'retail',
  'manufacturing',
  'hospitality',
  'real_estate',
  'logistics',
  'energy',
  'media',
  'other',
] as const
export type Industry = (typeof INDUSTRIES)[number]

export const COMPANY_SIZES = ['1-10', '11-50', '51-200', '201-1000', '1000+'] as const
export type CompanySize = (typeof COMPANY_SIZES)[number]

export const DATE_FORMATS = ['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'DD.MM.YYYY'] as const
export type DateFormat = (typeof DATE_FORMATS)[number]

/** Decimal / thousands separators: `1,234.56` · `1.234,56` · `1 234,56` · `1'234.56`. */
export const NUMBER_FORMATS = ['1,234.56', '1.234,56', '1 234,56', "1'234.56"] as const
export type NumberFormat = (typeof NUMBER_FORMATS)[number]

export type WeekStart = 'monday' | 'sunday' | 'saturday'

export interface OnboardingCompany {
  name: string
  industry: Industry | null
  size: CompanySize | null
  country: string | null
  website: string | null
}

export interface OnboardingBranding {
  logo_url: string | null
  brand_color: string | null
}

export interface OnboardingLocalisation {
  language: string
  timezone: string
  currency: string
  date_format: DateFormat
  number_format: NumberFormat
  week_start: WeekStart
}

export interface OnboardingInvite {
  email: string
  role: 'admin' | 'member'
}

export interface OnboardingFirstForm {
  choice: 'blank' | 'template' | null
  template_key: StarterTemplateKey | null
}

export interface Onboarding {
  status: 'not_started' | 'in_progress' | 'completed'
  current_step: OnboardingStep
  steps: Record<OnboardingStep, OnboardingStepStatus>
  company: OnboardingCompany
  branding: OnboardingBranding
  localisation: OnboardingLocalisation
  invites: OnboardingInvite[]
  first_form: OnboardingFirstForm
}

/** PATCH /onboarding body. `skip` marks the step skipped without data. */
export type OnboardingPatch =
  | { step: 'company'; action: 'save'; data: OnboardingCompany }
  | { step: 'branding'; action: 'save'; data: { logo_upload_id: string | null; brand_color: string | null } }
  | { step: 'localisation'; action: 'save'; data: OnboardingLocalisation }
  | { step: 'team'; action: 'save'; data: { invites: OnboardingInvite[] } }
  | { step: 'first_form'; action: 'save'; data: OnboardingFirstForm }
  | { step: OnboardingStep; action: 'skip' }

/** logo (onboarding / settings, admins) · form_image (image blocks in forms, any member). */
export type UploadPurpose = 'logo' | 'form_image' | 'share_image'

/** POST /uploads → where to PUT the file (pre-signed, SECURITY-PROTOCOL.md). */
export interface UploadTicket {
  upload_id: string
  upload_url: string
  method: 'PUT'
  headers: Record<string, string>
  max_bytes: number
  expires_at: string
}

/** POST /uploads/{id}/complete */
export interface UploadedFile {
  id: string
  url: string
  content_type: string
  size: number
}
