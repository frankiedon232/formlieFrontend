<!--
  Share → Embed (F10 M3, decision 94): which websites may show the form in a frame — any website,
  or only the ones listed (pasted addresses are tidied to `example.com`, `*.example.com` covers
  sub-sites). Others get the browser's "refused to connect". The embed code itself (with live
  preview) is one click away. Saved with the rest of the page.
-->
<script setup lang="ts">
import type { FormShareSettings, FormSummary, ShareDraft } from '#shared/types/forms'
import { MAX_EMBED_DOMAINS, normaliseEmbedDomain } from '#shared/utils/urls/embed-domains'
import { formLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ settings: FormShareSettings; form: FormSummary }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const config = useRuntimeConfig().public
const request = useRequestURL()
const tenant = useTenant()

const modes = computed(() => [
  { value: 'any', label: t('share.embed.any'), description: t('share.embed.anyDesc') },
  { value: 'listed', label: t('share.embed.listed'), description: t('share.embed.listedDesc') },
])
const mode = computed({
  get: () => (draft.value.embedLimited ? 'listed' : 'any'),
  set: value => (draft.value.embedLimited = value === 'listed'),
})

/** Every added site is tidied; anything that isn't a website is taken out again and said why. */
const refused = ref<string | null>(null)
function setDomains(values: string[]) {
  const tidy: string[] = []
  refused.value = null
  for (const value of values) {
    const domain = normaliseEmbedDomain(value)
    if (!domain) refused.value = value
    else if (!tidy.includes(domain)) tidy.push(domain)
  }
  draft.value.domains = tidy.slice(0, MAX_EMBED_DOMAINS)
}

const embedOpen = ref(false)
const embedUrl = computed(() => formLink(publicHosts(config, request.port), props.form.custom_link || props.form.public_key, 'embed', tenant.profile.value?.subdomain ?? null))
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start justify-between gap-3">
      <div class="flex items-start gap-3">
        <UIcon name="i-lucide-code-xml" class="mt-0.5 size-5 shrink-0 text-muted" />
        <div>
          <h2 class="text-sm font-semibold text-highlighted">{{ t('share.embed.title') }}</h2>
          <p class="text-xs text-muted">{{ t('share.embed.desc') }}</p>
        </div>
      </div>
      <UButton :label="t('forms.overview.embedCode')" icon="i-lucide-code-xml" color="neutral" variant="outline" size="xs" class="shrink-0" @click="embedOpen = true" />
    </div>

    <URadioGroup v-model="mode" :items="modes" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" :aria-label="t('share.embed.title')" />

    <div v-if="draft.embedLimited" class="mt-4 flex flex-col gap-2">
      <UFormField :label="t('share.embed.sites')" :description="t('share.embed.sitesHint', { n: MAX_EMBED_DOMAINS })" :error="refused ? t('share.embed.invalid', { site: refused }) : undefined">
        <UInputTags
          :model-value="draft.domains"
          :placeholder="draft.domains.length ? '' : t('share.embed.placeholder')"
          :max="MAX_EMBED_DOMAINS"
          add-on-paste
          add-on-blur
          add-on-tab
          :delimiter="/[\s,;]+/"
          icon="i-lucide-globe"
          class="w-full"
          :ui="{ itemText: 'font-mono' }"
          @update:model-value="v => setDomains(v as string[])"
        />
      </UFormField>
      <p class="flex items-start gap-1.5 text-xs text-muted">
        <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('share.embed.formalieAllowed') }}
      </p>
    </div>
    <FormsShareEmbedModal v-model:open="embedOpen" :url="embedUrl" :form-name="form.name" :live="form.status === 'published'" />
  </UCard>
</template>
