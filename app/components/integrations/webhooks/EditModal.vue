<!--
  New / edit webhook (F13 M6): a name, the HTTPS address that receives the calls (checked as you
  type: public hosts only), the events, every form or chosen ones, on / off. A new webhook returns
  its signing secret once (the page shows it).
-->
<script setup lang="ts">
import type { FormSummary } from '#shared/types/forms'
import { WEBHOOK_EVENTS, type Webhook, type WebhookEvent, type WebhookSaveRequest, type WebhookWithSecret } from '#shared/types/integrations'
import { checkWebhookUrl, eventLabelKey } from '#shared/utils/integrations/webhooks'

const props = defineProps<{ webhook?: Webhook | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [webhook: Webhook]; created: [result: WebhookWithSecret] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const state = reactive({ name: '', url: '', events: [] as WebhookEvent[], scope: 'all' as 'all' | 'some', forms: [] as string[], enabled: true })
const forms = ref<FormSummary[]>([])
const shown = ref(false)
watch(open, async value => {
  if (!value) return
  shown.value = false
  const hook = props.webhook
  Object.assign(state, { name: hook?.name ?? '', url: hook?.url ?? 'https://', events: hook ? [...hook.events] : ['response.created'], scope: hook?.forms.length ? 'some' : 'all', forms: hook?.forms.map(form => form.id) ?? [], enabled: hook?.enabled ?? true })
  try {
    forms.value = (await api.list<FormSummary>('/forms', { page_size: 100, sort: 'name' }, { background: true })).data
  } catch {
    forms.value = []
  }
})
const eventItems = computed(() => WEBHOOK_EVENTS.map(value => ({ value, label: t(eventLabelKey(value)), description: t(`integrations.webhooks.eventHint.${value.replace('.', '_')}`) })))
const formItems = computed(() => forms.value.map(form => ({ value: form.id, label: form.name })))
const scopes = computed(() => [
  { value: 'all', label: t('integrations.webhooks.allForms') },
  { value: 'some', label: t('integrations.webhooks.someForms') },
])
const urlProblem = computed(() => checkWebhookUrl(state.url, { allowLocal: import.meta.dev }))
const errors = computed(() => ({
  name: !state.name.trim() ? t('apiService.invalid.required') : undefined,
  url: urlProblem.value ? t(`integrations.webhooks.invalid.${urlProblem.value}`) : undefined,
  events: !state.events.length ? t('integrations.webhooks.invalid.events') : undefined,
  forms: state.scope === 'some' && !state.forms.length ? t('integrations.webhooks.invalid.forms') : undefined,
}))

const saving = ref(false)
async function save() {
  shown.value = true
  if (Object.values(errors.value).some(Boolean) || saving.value) return
  saving.value = true
  try {
    const body: WebhookSaveRequest = { name: state.name.trim(), url: state.url.trim(), events: state.events, form_ids: state.scope === 'all' ? [] : state.forms, enabled: state.enabled }
    if (props.webhook) emit('saved', (await api.patch<Webhook>(`/webhooks/${props.webhook.id}`, body)).data)
    else emit('created', (await api.post<WebhookWithSecret>('/webhooks', body)).data)
    open.value = false
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="webhook ? t('integrations.webhooks.editTitle') : t('integrations.webhooks.newTitle')" :description="t('integrations.webhooks.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form id="webhook-form" class="flex flex-col gap-5" @submit.prevent="save">
        <UFormField :label="t('integrations.webhooks.col.name')" :error="shown ? errors.name : undefined" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t('integrations.webhooks.namePlaceholder')" />
        </UFormField>
        <UFormField :label="t('integrations.webhooks.col.url')" :error="shown || state.url.length > 8 ? errors.url : undefined" :help="t('integrations.webhooks.urlHelp')" required>
          <UInput v-model="state.url" maxlength="2000" class="w-full" :ui="{ base: 'font-mono text-sm' }" dir="ltr" placeholder="https://example.com/hooks/formalie" />
        </UFormField>
        <UFormField :label="t('integrations.webhooks.col.events')" :error="shown ? errors.events : undefined">
          <UCheckboxGroup v-model="state.events" :items="eventItems" color="neutral" variant="card" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2' }" />
        </UFormField>
        <UFormField :label="t('integrations.webhooks.col.forms')" :error="shown ? errors.forms : undefined">
          <div class="flex flex-col gap-2 sm:flex-row">
            <USelect v-model="state.scope" :items="scopes" class="w-full sm:w-44" />
            <USelectMenu v-if="state.scope === 'some'" v-model="state.forms" :items="formItems" value-key="value" multiple :placeholder="t('integrations.webhooks.pickForms')" class="min-w-0 flex-1" />
          </div>
        </UFormField>
        <USwitch v-model="state.enabled" :label="t('integrations.webhooks.enabled')" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="webhook-form" :label="webhook ? t('common.save') : t('integrations.webhooks.create')" color="neutral" :loading="saving" />
      </div>
    </template>
  </AppModal>
</template>
