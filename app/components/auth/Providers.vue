<!--
  Social sign-in / sign-up buttons — only the providers enabled for this host (public profile):
  manage.* offers them all for the first signup; a workspace shows the ones its admin enabled.
  One row with a "Sign in with / Sign up with" caption (owner, 2026-10-02). Each goes to the backend's OAuth start endpoint
  (a plain redirect, not an enveloped call).
-->
<script setup lang="ts">
import type { AuthProvider } from '#shared/types/auth'

const props = withDefaults(
  defineProps<{
    providers: readonly AuthProvider[]
    /** signup = create a new workspace with this provider (manage.*); login = sign in to this workspace. */
    intent?: 'login' | 'signup'
  }>(),
  { intent: 'login' },
)
const { t } = useI18n()
const config = useRuntimeConfig()

const ICONS: Record<Exclude<AuthProvider, 'password'>, string> = {
  google: 'i-simple-icons-google',
  microsoft: 'i-simple-icons-microsoft',
  apple: 'i-simple-icons-apple',
  facebook: 'i-simple-icons-facebook',
}

const social = computed(() =>
  props.providers.filter((p): p is Exclude<AuthProvider, 'password'> => p !== 'password'),
)

// Brand names (not translated). One row: name + logo for up to 2, logo only (with tooltip) for 3+.
const NAMES: Record<Exclude<AuthProvider, 'password'>, string> = {
  google: 'Google',
  microsoft: 'Microsoft',
  apple: 'Apple',
  facebook: 'Facebook',
}
const compact = computed(() => social.value.length > 2)
const columns = computed(
  () => ({ 1: 'grid-cols-1', 2: 'grid-cols-2', 3: 'grid-cols-3' })[social.value.length] ?? 'grid-cols-4',
)
</script>

<template>
  <div v-if="social.length" class="flex flex-col gap-2.5">
    <p class="text-sm font-medium text-default">
      {{ props.intent === 'signup' ? t('auth.providers.signUpWith') : t('auth.providers.signInWith') }}
    </p>
    <div class="grid gap-2.5" :class="columns">
      <UTooltip
        v-for="provider in social"
        :key="provider"
        :text="t(`auth.providers.${provider}`)"
        :disabled="!compact"
      >
        <UButton
          :icon="ICONS[provider]"
          :label="compact ? undefined : NAMES[provider]"
          :aria-label="t(`auth.providers.${provider}`)"
          :to="`${config.public.apiBase}/auth/oauth/${provider}/start?intent=${props.intent}`"
          external
          color="neutral"
          variant="outline"
          size="xl"
          block
          class="justify-center font-medium"
          :ui="{ leadingIcon: 'size-5' }"
        />
      </UTooltip>
    </div>
  </div>
</template>
