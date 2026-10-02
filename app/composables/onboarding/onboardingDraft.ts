import type {
  Onboarding,
  OnboardingCompany,
  OnboardingFirstForm,
  OnboardingInvite,
  OnboardingLocalisation,
  OnboardingPatch,
  OnboardingStep,
} from '#shared/types/onboarding'
import { COUNTRY_CURRENCIES } from '#shared/utils/platform/countries'

export interface OnboardingBrandingDraft {
  /** Saved URL, or a local object URL while a new logo is pending. */
  logo_url: string | null
  logo_upload_id: string | null
  brand_color: string | null
}

/** What the wizard edits (and the live preview shows) before each step is saved. */
export interface OnboardingDraft {
  company: OnboardingCompany
  branding: OnboardingBrandingDraft
  localisation: OnboardingLocalisation
  invites: OnboardingInvite[]
  first_form: OnboardingFirstForm
}

/**
 * Editable copy of the server state with sensible defaults for steps not done yet:
 * country from the browser language, timezone from the device, language from the UI,
 * currency / date / number / week start from the country.
 */
export function createOnboardingDraft(state: Onboarding, uiLanguage: string): OnboardingDraft {
  const company = { ...state.company }
  if (!company.country && state.steps.company !== 'done') company.country = browserCountry()
  const localisation = { ...state.localisation }
  if (state.steps.localisation !== 'done') {
    const country = company.country
    Object.assign(localisation, {
      language: uiLanguage,
      timezone: browserTimezone(),
      currency: (country && COUNTRY_CURRENCIES[country]) || localisation.currency,
      date_format: suggestDateFormat(country),
      number_format: suggestNumberFormat(country),
      week_start: suggestWeekStart(country),
    })
  }
  return {
    company,
    branding: {
      logo_url: state.branding.logo_url,
      logo_upload_id: null,
      brand_color: state.branding.brand_color,
    },
    localisation,
    invites: state.invites.length
      ? state.invites.map(invite => ({ ...invite }))
      : [
          { email: '', role: 'member' },
          { email: '', role: 'member' },
        ],
    first_form: { ...state.first_form },
  }
}

/** PATCH body for saving one step from the draft (empty invite rows are dropped). */
export function onboardingPatchFor(step: OnboardingStep, draft: OnboardingDraft): OnboardingPatch {
  switch (step) {
    case 'company':
      return { step, action: 'save', data: draft.company }
    case 'branding':
      return {
        step,
        action: 'save',
        data: { logo_upload_id: draft.branding.logo_upload_id, brand_color: draft.branding.brand_color },
      }
    case 'localisation':
      return { step, action: 'save', data: draft.localisation }
    case 'team':
      return {
        step,
        action: 'save',
        data: {
          invites: draft.invites
            .filter(invite => invite.email.trim())
            .map(invite => ({ ...invite, email: invite.email.trim().toLowerCase() })),
        },
      }
    default:
      return { step: 'first_form', action: 'save', data: draft.first_form }
  }
}
