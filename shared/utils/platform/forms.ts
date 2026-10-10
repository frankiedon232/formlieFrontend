/**
 * Formalie's own forms (owner 2026-10-10): we collect our own data with our own forms. Contact support and the
 * Enterprise enquiry are published forms of Formalie's workspace, opened in the app's browser window (AppBrowser);
 * what people send is an ordinary response the Formalie team reads in the platform admin. The app fills in what it
 * knows through the address (hidden fields and fields that allow it, shared/utils/forms/prefill.ts).
 */
export const PLATFORM_FORMS = { support: 'FormalieHp', enterprise: 'FormalieEn' } as const
export type PlatformForm = keyof typeof PLATFORM_FORMS
