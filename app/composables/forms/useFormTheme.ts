import type { InjectionKey } from 'vue'
import type { FormTheme, WorkspaceBranding } from '#shared/utils/forms/theme'

/** The workspace's branding (logo + brand colour from onboarding) — the default theme's source. */
export function useWorkspaceBranding() {
  const { profile } = useTenant()
  return computed<WorkspaceBranding>(() => ({
    logo_url: profile.value?.logo_url ?? null,
    primary: profile.value?.colors.primary ?? null,
  }))
}

/** The full theme of a schema's `theme` tokens (workspace default ← stored tokens). */
export function useFormTheme(stored: () => unknown) {
  const branding = useWorkspaceBranding()
  return computed(() => resolveTheme(stored(), branding.value))
}

// ── Control style for inputs inside a themed form ──────────────────────────────────────
interface ControlStyle {
  size: 'sm' | 'md' | 'lg'
  variant: 'outline' | 'soft' | 'none'
  ui: { base?: string }
}
const CONTROL_STYLE: InjectionKey<ComputedRef<ControlStyle>> = Symbol('form-control-style')

/** Called by the themed form page: inputs below follow the theme's size and style. */
export function provideControlStyle(theme: ComputedRef<FormTheme>) {
  provide(
    CONTROL_STYLE,
    computed(() => {
      const { size, style } = theme.value.inputs
      return {
        size,
        variant: style === 'soft' ? 'soft' : style === 'underline' ? 'none' : 'outline',
        ui:
          style === 'underline'
            ? { base: 'rounded-none border-b border-accented px-0 focus-visible:border-(--ui-primary)' }
            : {},
      }
    }),
  )
}

/** Props to spread on Nuxt UI inputs (`v-bind="control"`); plain defaults outside a themed form. */
export function useControlStyle() {
  return inject(
    CONTROL_STYLE,
    computed<ControlStyle>(() => ({ size: 'md', variant: 'outline', ui: {} })),
  )
}
