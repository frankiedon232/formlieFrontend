<!--
  Share → Custom link (F10 M3): a readable address instead of the random key —
  `https://{forms | sub}.formalie.com/{custom-link}/fill`. Checked while typing
  (GET /forms/{id}/share/link-check): free · taken (by which of your forms) or reserved, with up to
  three free suggestions · invalid. Links are unique per address: each workspace subdomain has its own.
  The key keeps working, so links already shared never break.
-->
<script setup lang="ts">
import type { CustomLinkCheck, FormShareSettings, FormSummary, ShareDraft } from '#shared/types/forms'
import { formLink, formsHostFor, publicHosts, tidyCustomLink } from '#shared/utils/urls/public'

const props = defineProps<{ settings: FormShareSettings; form: FormSummary }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const ok = defineModel<boolean>('ok', { default: true })
const { t } = useI18n()
const api = useApi()
const config = useRuntimeConfig().public
const request = useRequestURL()
const tenant = useTenant()

const hosts = computed(() => publicHosts(config, request.port))
const host = computed(() => `${formsHostFor(hosts.value, tenant.profile.value?.subdomain ?? null)}${hosts.value.port ?? ''}`)
const keyLink = computed(() => formLink(hosts.value, props.form.public_key, 'fill', tenant.profile.value?.subdomain ?? null))
const preview = computed(() => (draft.value.link ? formLink(hosts.value, draft.value.link, 'fill', tenant.profile.value?.subdomain ?? null) : keyLink.value))

const result = ref<CustomLinkCheck | null>(null)
const checking = ref(false)
const unchanged = computed(() => draft.value.link === (props.settings.custom_link ?? ''))

/** Typing: lower case, other characters become hyphens (cleaned fully when leaving the field). */
function typed(value: string | number) {
  draft.value.link = String(value).toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/-{2,}/g, '-').replace(/^-/, '').slice(0, 60)
}
const tidy = () => (draft.value.link = tidyCustomLink(draft.value.link))

let latest = 0
const check = useDebounceFn(async (value: string) => {
  const ticket = ++latest
  try {
    const { data } = await api.get<CustomLinkCheck>(`/forms/${props.form.id}/share/link-check`, { value }, { background: true })
    if (ticket === latest) result.value = data
  } catch {
    if (ticket === latest) result.value = null
  } finally {
    if (ticket === latest) checking.value = false
  }
}, 350)

watch(
  () => draft.value.link,
  value => {
    result.value = null
    if (!value || unchanged.value) {
      checking.value = false
      ok.value = true
      return
    }
    checking.value = true
    ok.value = false
    void check(tidyCustomLink(value))
  },
  { immediate: true },
)
watch(result, value => (ok.value = !draft.value.link || unchanged.value || (!!value?.available && value.value === draft.value.link)))

const status = computed(() => {
  if (!draft.value.link || unchanged.value) return null
  if (checking.value) return { icon: 'i-lucide-loader-circle', spin: true, color: 'text-muted', text: t('share.link.checking') }
  if (!result.value) return null
  if (result.value.available) return { icon: 'i-lucide-circle-check', spin: false, color: 'text-success', text: t('share.link.free') }
  return { icon: 'i-lucide-circle-x', spin: false, color: 'text-error', text: t(`share.link.${result.value.reason ?? 'invalid'}`) }
})
const { copy } = useClipboard({ legacy: true })
const toast = useToast()
function copyPreview() {
  copy(preview.value)
  toast.add({ title: t('share.link.copied'), icon: 'i-lucide-check', color: 'success' })
}
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start gap-3">
      <UIcon name="i-lucide-link-2" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.link.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.link.desc') }}</p>
      </div>
    </div>
    <UFormField :label="t('share.link.label')" :hint="t('share.link.hint')">
      <div class="flex min-w-0 items-stretch overflow-hidden rounded-md border border-default focus-within:ring-2 focus-within:ring-inverted" dir="ltr">
        <span class="hidden shrink-0 items-center border-e border-default bg-elevated px-2 text-xs text-muted sm:flex">{{ host }}/</span>
        <UInput
          :model-value="draft.link"
          variant="none"
          :placeholder="t('share.link.placeholder')"
          class="min-w-0 flex-1"
          :ui="{ base: 'font-mono text-sm' }"
          :aria-label="t('share.link.label')"
          @update:model-value="typed"
          @blur="tidy"
        />
        <span class="flex shrink-0 items-center border-s border-default bg-elevated px-2 text-xs text-muted">/fill</span>
      </div>
    </UFormField>
    <div class="mt-2 flex min-h-5 flex-wrap items-center gap-x-3 gap-y-1 text-xs" aria-live="polite">
      <span v-if="status" class="flex items-center gap-1.5" :class="status.color">
        <UIcon :name="status.icon" class="size-3.5" :class="status.spin ? 'animate-spin' : ''" />{{ status.text }}
      </span>
      <UButton v-if="draft.link" :label="t('share.link.remove')" icon="i-lucide-x" color="neutral" variant="link" size="xs" class="ms-auto px-0" @click="draft.link = ''" />
    </div>
    <!-- Taken by one of your forms: which one, with a way to open it. -->
    <div v-if="result?.taken_by" class="mt-3 flex items-center gap-3 rounded-md border border-default bg-elevated/40 p-3">
      <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-default">
        <UIcon name="i-lucide-file-text" class="size-4 text-muted" />
      </span>
      <div class="min-w-0 flex-1">
        <p class="text-xs text-muted">{{ result.taken_by.link ? t('share.link.usedBy') : t('share.link.usedByKey') }}</p>
        <div class="flex min-w-0 items-center gap-2">
          <span class="truncate text-sm font-medium text-highlighted">{{ result.taken_by.name }}</span>
          <DataStatusBadge :status="result.taken_by.status" />
        </div>
      </div>
      <UButton :label="t('share.link.openForm')" icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" :to="`/forms/${result.taken_by.id}`" target="_blank" />
    </div>
    <!-- Taken or reserved: free links close to it, one click to use. -->
    <div v-if="result?.suggestions.length" class="mt-2 flex flex-wrap items-center gap-1.5">
      <span class="text-xs text-muted">{{ t('share.link.try') }}</span>
      <UButton
        v-for="suggestion in result.suggestions"
        :key="suggestion"
        :label="suggestion"
        icon="i-lucide-sparkles"
        color="neutral"
        variant="outline"
        size="xs"
        class="rounded-full font-mono"
        @click="draft.link = suggestion"
      />
    </div>
    <div class="mt-3 flex items-center gap-2 rounded-md bg-elevated/50 px-3 py-2">
      <code class="min-w-0 flex-1 truncate text-xs text-highlighted" dir="ltr">{{ preview }}</code>
      <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :aria-label="t('share.link.copy')" @click="copyPreview" />
    </div>
    <p class="mt-2 text-xs text-muted">{{ t('share.link.keyStays') }}</p>
  </UCard>
</template>
