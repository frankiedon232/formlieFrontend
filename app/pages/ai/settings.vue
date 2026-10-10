<!--
  AI assistant → Settings & usage (F19 M1): switch the assistant on or off for the workspace, choose what
  it may read (forms, responses, data sources), keep personal data out, how long requests are kept; this
  month's use of the allowance. Saving applies at once (audited); people without ai.settings see it read-only.
-->
<script setup lang="ts">
import { AI_KEEP_DAYS, AI_SOURCES, type AiSettings, type AiUsage } from '#shared/types/ai'

definePageMeta({ breadcrumb: 'nav.aiSettings' })
const { t, d } = useI18n()
useHead({ title: () => t('nav.aiSettings') })
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { number } = useFormat()
const { can } = useCan()
const ai = useAi()
const manage = computed(() => can('ai.settings'))

type Draft = Pick<AiSettings, 'enabled' | 'sources' | 'mask_personal' | 'keep_days'>
const draft = ref<Draft | null>(null)
const copyOf = (settings: AiSettings): Draft => ({ enabled: settings.enabled, sources: { ...settings.sources }, mask_personal: settings.mask_personal, keep_days: settings.keep_days })
const usage = ref<AiUsage | null>(null)
onMounted(async () => {
  const settings = await ai.load(true)
  if (settings) draft.value = copyOf(settings)
  try {
    usage.value = (await api.get<AiUsage>('/ai/usage')).data
  } catch (error) {
    handle(error, { silent: true })
  }
})
const dirty = computed(() => !!draft.value && !!ai.settings.value && JSON.stringify(draft.value) !== JSON.stringify(copyOf(ai.settings.value)))
const saving = ref(false)
async function save() {
  if (!draft.value || !dirty.value || !manage.value || saving.value) return
  saving.value = true
  try {
    draft.value = copyOf(await ai.save(draft.value))
    toast.add({ title: t('ai.settings.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
const discard = () => ai.settings.value && (draft.value = copyOf(ai.settings.value))
defineShortcuts({ meta_s: { usingInput: true, handler: () => void save() } })
onBeforeRouteLeave(async () => (dirty.value ? await useConfirm()({ title: t('ai.settings.leaveTitle'), description: t('ai.settings.leaveDesc'), confirmLabel: t('ai.settings.leave'), danger: true }) : true))

const updated = computed(() => (ai.settings.value?.updated_at && ai.settings.value.updated_by ? { at: ai.settings.value.updated_at, by: ai.settings.value.updated_by.name } : null))
const keepOptions = computed(() => AI_KEEP_DAYS.map(days => ({ value: days, label: t('ai.settings.days', { n: days }) })))
const used = computed(() => (usage.value?.limit ? Math.min(100, Math.round((usage.value.used / usage.value.limit) * 100)) : 0))
const renews = computed(() => {
  if (!usage.value) return ''
  const end = new Date(`${usage.value.period.end}T12:00:00`)
  end.setDate(end.getDate() + 1)
  return d(end, { day: 'numeric', month: 'long' })
})
const SOURCE_ICONS = { forms: 'i-lucide-file-text', responses: 'i-lucide-inbox', data: 'i-lucide-database' } as const
</script>

<template>
  <SettingsPage id="ai-settings" plain :title="t('nav.aiSettings')" :subtitle="t('ai.section.settings')" icon="i-lucide-sliders-horizontal" :form="manage ? { dirty, saving, updated } : undefined" @save="save" @discard="discard">
    <AppEmpty v-if="ai.failed.value && !draft" icon="i-lucide-cloud-off" :title="t('settings.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: () => ai.load(true).then(s => s && (draft = copyOf(s))) }]" />
    <div v-else-if="!draft" class="flex flex-col gap-6"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
    <div v-else class="flex flex-col gap-6">
      <UAlert v-if="!manage" color="neutral" variant="subtle" icon="i-lucide-lock" :title="t('ai.settings.readOnly')" />

      <SettingsBlock :title="t('ai.settings.assistant')" :description="t('ai.settings.assistantHint')" icon="i-lucide-sparkles">
        <div class="flex items-center gap-3 rounded-lg border border-default p-3">
          <span class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="text-sm font-medium text-highlighted">{{ t('ai.settings.enabled') }}</span>
            <span class="text-xs text-muted">{{ draft.enabled ? t('ai.settings.enabledOn') : t('ai.settings.enabledOff') }}</span>
          </span>
          <USwitch v-model="draft.enabled" color="neutral" :disabled="!manage" :aria-label="t('ai.settings.enabled')" />
        </div>
      </SettingsBlock>

      <SettingsBlock :title="t('ai.settings.reads')" :description="t('ai.settings.readsHint')" icon="i-lucide-eye">
        <div class="flex flex-col divide-y divide-default rounded-lg border border-default">
          <div v-for="source in AI_SOURCES" :key="source" class="flex items-center gap-3 px-3 py-3">
            <UIcon :name="SOURCE_ICONS[source]" class="size-4 shrink-0 text-muted" />
            <span class="flex min-w-0 flex-1 flex-col gap-0.5">
              <span class="text-sm font-medium text-highlighted">{{ t(`ai.source.${source}.label`) }}</span>
              <span class="text-xs text-muted">{{ t(`ai.source.${source}.hint`) }}</span>
            </span>
            <USwitch v-model="draft.sources[source]" color="neutral" size="sm" :disabled="!manage || !draft.enabled" :aria-label="t(`ai.source.${source}.label`)" />
          </div>
        </div>
      </SettingsBlock>

      <SettingsBlock :title="t('ai.settings.privacy')" :description="t('ai.settings.privacyHint')" icon="i-lucide-shield-check">
        <div class="flex items-center gap-3 rounded-lg border border-default p-3">
          <span class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="text-sm font-medium text-highlighted">{{ t('ai.settings.mask') }}</span>
            <span class="text-xs text-muted">{{ t('ai.settings.maskHint') }}</span>
          </span>
          <USwitch v-model="draft.mask_personal" color="neutral" :disabled="!manage || !draft.enabled" :aria-label="t('ai.settings.mask')" />
        </div>
        <UFormField :label="t('ai.settings.keep')" :description="t('ai.settings.keepHint')">
          <USelect v-model="draft.keep_days" :items="keepOptions" class="w-48" :disabled="!manage" />
        </UFormField>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('ai.settings.processing') }}</p>
      </SettingsBlock>

      <SettingsBlock :title="t('ai.settings.usage')" :description="t('ai.settings.usageHint')" icon="i-lucide-gauge">
        <div v-if="!usage" class="flex flex-col gap-2"><USkeleton class="h-4 w-48" /><USkeleton class="h-2 w-full" /></div>
        <div v-else class="flex flex-col gap-3 rounded-lg border border-default p-4">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="text-sm text-default"><span class="text-2xl font-semibold text-highlighted tabular-nums">{{ number(usage.used) }}</span> / {{ number(usage.limit) }} {{ t('ai.settings.credits') }}</span>
            <span class="text-xs text-muted">{{ t('ai.settings.renews', { date: renews }) }}</span>
          </div>
          <UProgress :model-value="used" size="sm" :color="used >= 90 ? 'error' : used >= 75 ? 'warning' : 'neutral'" />
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
            <span>{{ t('ai.settings.planNote') }}</span>
            <UButton v-if="can('ai.history')" :label="t('nav.aiHistory')" icon="i-lucide-history" color="neutral" variant="outline" size="xs" to="/ai/history" />
          </div>
        </div>
      </SettingsBlock>
    </div>
  </SettingsPage>
</template>
