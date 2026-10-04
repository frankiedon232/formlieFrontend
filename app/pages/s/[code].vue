<!--
  Short link `https://forms.formalie.com/s/{code}` (F10 M3, server-rendered): sends people straight
  on to the form's current link (custom link or key, on its own host) with a 302, so a link on a
  poster keeps working when the form's address changes. Unknown or removed codes: a clear 404 page.
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
const config = useRuntimeConfig()
const requestFetch = import.meta.server ? useRequestFetch() : null
const host = import.meta.server ? useRequestURL().host : ''
const api = useApi()

const { data } = await useAsyncData(`short:${code}`, async () => {
  if (import.meta.server && requestFetch)
    return requestFetch<{ data?: { target: string }; error?: { code: string } }>(`/_ssr/short/${code}`, {
      headers: { 'x-formalie-internal': String(config.internalToken ?? ''), 'x-forwarded-host': host },
      ignoreResponseError: true,
    })
  try {
    return { data: (await api.get<{ target: string }>(`/public/short/${code}`)).data }
  } catch (error) {
    return { error: { code: (error as { code?: string }).code ?? 'FRM-GEN-5000' } }
  }
})

const target = data.value?.data?.target
if (target) await navigateTo(target, { external: true, redirectCode: 302 })
else if (import.meta.server) {
  const event = useRequestEvent()
  if (event) setResponseStatus(event, data.value?.error?.code === 'FRM-FORM-1001' ? 404 : 503)
}
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
