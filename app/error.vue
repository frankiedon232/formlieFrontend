<!-- Global error page (404 and unexpected errors). Rendered instead of app.vue, so it sets up UApp itself. -->
<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
const { t } = useI18n()
const { current, uiLocale } = useAppLocale()

const notFound = computed(() => props.error.statusCode === 404)

const display = computed(() => ({
  statusCode: props.error.statusCode,
  statusMessage: notFound.value ? t('error.notFoundTitle') : t('error.genericTitle'),
  message: notFound.value ? t('error.notFoundDesc') : t('error.genericDesc'),
}))

useHead({
  title: () => display.value.statusMessage,
  htmlAttrs: { lang: () => current.value.language, dir: () => current.value.dir },
})

if (import.meta.dev && !notFound.value) console.error(props.error)
</script>

<template>
  <UApp :locale="uiLocale">
    <div class="flex min-h-dvh flex-col bg-muted">
      <header class="flex items-center justify-end gap-1 px-4 py-3 sm:px-6">
        <AppLocaleSwitch />
        <UColorModeButton />
      </header>
      <UError
        :error="display"
        redirect="/forms"
        :clear="{ label: t('common.goHome'), icon: 'i-lucide-house', size: 'lg' }"
        class="flex-1"
      />
    </div>
  </UApp>
</template>
