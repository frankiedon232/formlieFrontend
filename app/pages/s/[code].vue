<!--
  Short link `https://forms.formalie.com/s/{code}` (F10 M3): sends people straight on to the form's
  current link (custom link or key, on its own host), so a link on a poster keeps working when the
  form's address changes. In production the Cloudflare Worker answers it with a 302 before the app
  loads; this page is the fallback (and development): it asks the public API and replaces itself
  with the destination. Unknown or removed codes: a clear "not found" card.
-->
<script setup lang="ts">
import { SHORT_CODE_PATTERN } from '#shared/utils/urls/public'

definePageMeta({
  layout: 'public',
  auth: false,
  public: true,
  validate: route => SHORT_CODE_PATTERN.test(String(route.params.code ?? '')),
})
const { t } = useI18n()
const route = useRoute()
const code = String(route.params.code)
const api = useApi()

const { data } = await useAsyncData(`short:${code}`, async () => {
  try {
    return { data: (await api.get<{ target: string }>(`/public/short/${code}`)).data }
  } catch (error) {
    return { error: { code: (error as { code?: string }).code ?? 'FRM-GEN-5000' } }
  }
})

/** Only web addresses are followed (never `javascript:` or other schemes). */
const target = (() => {
  const value = data.value?.data?.target
  if (!value) return null
  try {
    return ['https:', 'http:'].includes(new URL(value, location.href).protocol) ? value : null
  } catch {
    return null
  }
})()
// replace: Back returns to where the person came from, not to this page.
if (target) await navigateTo(target, { external: true, replace: true })
useSeoMeta({ title: () => t('public.short.title'), robots: 'noindex, nofollow' })
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <div class="flex flex-1 items-center justify-center bg-elevated/40 px-4 py-16">
      <UCard class="w-full max-w-md" :ui="{ body: 'p-6 sm:p-8' }">
        <div class="flex flex-col items-center gap-3 text-center">
          <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
            <UIcon :name="target ? 'i-lucide-loader-circle' : 'i-lucide-link-2-off'" class="size-6 text-muted" :class="target ? 'animate-spin' : ''" />
          </span>
          <h1 class="text-lg font-semibold text-highlighted">{{ target ? t('public.short.opening') : t('public.short.title') }}</h1>
          <p v-if="!target" class="text-sm text-muted">{{ t('public.short.desc') }}</p>
        </div>
      </UCard>
    </div>
    <FormsRendererFrameFooter class="bg-default" :org="{ name: 'Formalie' }" :year="new Date().getFullYear()" slim />
  </div>
</template>
