<!--
  Settings → Email templates (F14 M4): one template in one language. Subject and text with its
  placeholders (click to insert at the cursor), Formalie's text until it is changed, "Use Formalie's
  text" to go back, a live preview in the workspace's look, and "Send me a test" (to the sent log).
  Edits go into the page's draft (`custom`), saved with the page.
-->
<script setup lang="ts">
import type { EmailSettings, EmailTemplateKey, EmailTemplateView, EmailText } from '#shared/types/emails'

const props = defineProps<{ templateKey: EmailTemplateKey; language: string }>()
const custom = defineModel<EmailSettings['custom']>({ required: true })
const emit = defineEmits<{ sent: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { busy, run } = useBusy()

const view = ref<EmailTemplateView | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  view.value = null
  try {
    view.value = (await api.get<EmailTemplateView>(`/settings/emails/templates/${props.templateKey}`, { language: props.language })).data
  } catch {
    failed.value = true
  }
}
watch(() => [props.templateKey, props.language], load, { immediate: true })

/** What is shown: the draft's own text, else Formalie's. Editing makes it the workspace's own; back to Formalie's text when it matches. */
const text = computed<EmailText | null>(() => custom.value[props.templateKey]?.[props.language] ?? view.value?.default ?? null)
const isCustom = computed(() => !!custom.value[props.templateKey]?.[props.language])
function update(part: keyof EmailText, value: string) {
  if (!text.value || !view.value) return
  const next = { ...text.value, [part]: value }
  const same = next.subject === view.value.default.subject && next.body === view.value.default.body
  const others = Object.entries(custom.value[props.templateKey] ?? {}).filter(([code]) => code !== props.language)
  const languages = Object.fromEntries(same ? others : [...others, [props.language, next]])
  const rest = Object.entries(custom.value).filter(([key]) => key !== props.templateKey)
  custom.value = Object.fromEntries(Object.keys(languages).length ? [...rest, [props.templateKey, languages]] : rest)
}
const reset = () => view.value && (update('subject', view.value.default.subject), update('body', view.value.default.body))

// Placeholders: inserted where the cursor is in the field last used
const target = ref<'subject' | 'body'>('body')
const bodyArea = useTemplateRef<{ textareaRef: HTMLTextAreaElement }>('bodyArea')
const subjectInput = useTemplateRef<{ inputRef: HTMLInputElement }>('subjectInput')
function insert(name: string) {
  if (!text.value) return
  const token = `{{${name}}}`
  const el = target.value === 'body' ? bodyArea.value?.textareaRef : subjectInput.value?.inputRef
  const value = text.value[target.value]
  const start = el?.selectionStart ?? value.length
  const end = el?.selectionEnd ?? value.length
  update(target.value, value.slice(0, start) + token + value.slice(end))
  nextTick(() => {
    el?.focus()
    el?.setSelectionRange(start + token.length, start + token.length)
  })
}

// Live preview, a moment after typing stops
const preview = ref<{ subject: string; html: string; from: string; reply_to: string | null } | null>(null)
const previewing = ref(false)
const refresh = useDebounceFn(async () => {
  if (!text.value?.subject.trim() || !text.value.body.trim()) return
  previewing.value = true
  try {
    preview.value = (await api.post<typeof preview.value>('/settings/emails/preview', { key: props.templateKey, language: props.language, ...text.value }, { background: true })).data
  } catch {
    preview.value = null
  } finally {
    previewing.value = false
  }
}, 350)
watch(text, () => void refresh(), { immediate: true, deep: true })

async function sendTest() {
  if (!text.value) return
  const sent = await run(async () => (await api.post<{ to: string }>('/settings/emails/test', { key: props.templateKey, language: props.language, ...text.value })).data)
  if (sent) {
    toast.add({ title: t('settings.emails.testSent', { to: sent.to }), color: 'success', icon: 'i-lucide-mail-check' })
    emit('sent')
  }
}
const empty = computed(() => !!text.value && (!text.value.subject.trim() || !text.value.body.trim()))
</script>

<template>
  <AppEmpty v-if="failed" size="sm" icon="i-lucide-cloud-off" :title="t('settings.emails.loadFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else-if="!text" class="grid gap-4 lg:grid-cols-2"><USkeleton class="h-72 rounded-lg" /><USkeleton class="h-72 rounded-lg" /></div>
  <div v-else class="grid gap-4 xl:grid-cols-2">
    <div class="flex min-w-0 flex-col gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <UBadge :label="isCustom ? t('settings.emails.own') : t('settings.emails.formalie')" :icon="isCustom ? 'i-lucide-pencil' : 'i-lucide-sparkles'" color="neutral" :variant="isCustom ? 'solid' : 'outline'" />
        <UButton v-if="isCustom" :label="t('settings.emails.reset')" icon="i-lucide-rotate-ccw" color="neutral" variant="link" size="xs" @click="reset" />
      </div>
      <UFormField :label="t('settings.emails.subject')" :error="!text.subject.trim() ? t('settings.invalid.subject') : undefined">
        <UInput ref="subjectInput" :model-value="text.subject" class="w-full" @focus="target = 'subject'" @update:model-value="value => update('subject', String(value))" />
      </UFormField>
      <UFormField :label="t('settings.emails.body')" :error="!text.body.trim() ? t('settings.invalid.body') : undefined">
        <UTextarea ref="bodyArea" :model-value="text.body" :rows="10" autoresize :maxrows="18" class="w-full" :ui="{ base: 'font-mono text-xs leading-relaxed' }" @focus="target = 'body'" @update:model-value="value => update('body', String(value))" />
      </UFormField>
      <div class="flex flex-col gap-1.5">
        <span class="text-xs text-muted">{{ t('settings.emails.placeholders') }}</span>
        <div class="flex flex-wrap gap-1.5">
          <UButton v-for="name in view?.variables ?? []" :key="name" :label="`{{${name}}}`" color="neutral" variant="soft" size="xs" class="font-mono" :aria-label="t('settings.emails.insert', { name: t(`settings.emails.var.${name}`) })" @click="insert(name)">
            <template #trailing><span class="font-sans text-[10px] text-muted">{{ t(`settings.emails.var.${name}`) }}</span></template>
          </UButton>
        </div>
      </div>
    </div>

    <div class="flex min-w-0 flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.emails.preview') }}</span>
        <UButton :label="t('settings.emails.sendTest')" icon="i-lucide-send" color="neutral" variant="outline" size="xs" :loading="busy" :disabled="empty" @click="sendTest" />
      </div>
      <div class="overflow-hidden rounded-lg border border-default" :class="previewing ? 'opacity-70' : ''">
        <div class="flex flex-col gap-0.5 border-b border-default bg-elevated/50 px-3 py-2 text-xs">
          <span class="truncate"><span class="text-muted">{{ t('settings.emails.from') }}</span> <span class="text-highlighted">{{ preview?.from }}</span></span>
          <span class="truncate font-medium text-highlighted">{{ preview?.subject }}</span>
        </div>
        <iframe v-if="preview" :srcdoc="preview.html" sandbox="" :title="t('settings.emails.preview')" class="h-96 w-full bg-white" />
        <USkeleton v-else class="h-96 rounded-none" />
      </div>
      <p class="text-xs text-muted">{{ t('settings.emails.sampleNote') }}</p>
    </div>
  </div>
</template>
