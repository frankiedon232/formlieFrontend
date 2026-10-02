<!--
  Social sign-in buttons — only the providers this workspace enabled (tenant public profile).
  Full-width, stacked, roomy (never truncated). Each goes to the backend's OAuth start endpoint
  (a plain redirect, not an enveloped call).
-->
<script setup lang="ts">
import type { AuthProvider } from '#shared/types/auth'

const props = defineProps<{ providers: readonly AuthProvider[] }>()
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
</script>

<template>
  <div v-if="social.length" class="flex flex-col gap-2.5">
    <UButton
      v-for="provider in social"
      :key="provider"
      :icon="ICONS[provider]"
      :label="t(`auth.providers.${provider}`)"
      :to="`${config.public.apiBase}/auth/oauth/${provider}/start`"
      external
      color="neutral"
      variant="outline"
      size="xl"
      block
      class="justify-center font-medium"
    />
  </div>
</template>
