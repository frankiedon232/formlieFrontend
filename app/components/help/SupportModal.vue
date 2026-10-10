<!--
  Contact support (F25, owner 2026-10-10): a form inside the app, like the Enterprise enquiry, sent to the
  Formalie team who answer it from the platform admin (the reply comes by email). What it is about, the area,
  a subject and the message, "urgent" when something is broken for the whole team; the email and the page it
  was sent from are filled in. After sending: a reference to quote, and the person's earlier requests.
-->
<script setup lang="ts">
import { z } from 'zod'
import { HELP_CATEGORIES, SUPPORT_TOPICS, type HelpCategory, type SupportRequest, type SupportTopic } from '#shared/types/help'

const { t } = useI18n()
const api = useApi()
const route = useRoute()
const session = useSession()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const support = useSupport()

interface Draft {
  topic: SupportTopic
  area: HelpCategory | null
  subject: string
  message: string
  urgent: boolean
  email: string
}
const blank = (): Draft => ({ topic: support.preset.value.topic ?? 'question', area: support.preset.value.area ?? null, subject: support.preset.value.subject ?? '', message: '', urgent: false, email: session.user.value?.email ?? '' })
const state = ref<Draft>(blank())
const sent = ref<SupportRequest | null>(null)
const earlier = ref<SupportRequest[] | null>(null)
/** The page it was opened from (before the help pages, when the help panel was used). */
const from = ref<string | null>(null)

watch(support.open, async value => {
  if (!value) return
  state.value = blank()
  sent.value = null
  from.value = route.fullPath
  try {
    earlier.value = (await api.get<SupportRequest[]>('/help/support-requests', undefined, { background: true })).data
  } catch (error) {
    handle(error, { silent: true })
    earlier.value = []
  }
})

const schema = computed(() =>
  z.object({
    subject: z.string().trim().min(3, t('help.contact.subjectShort')),
    message: z.string().trim().min(10, t('help.contact.messageShort')),
    email: z.email(t('billing.enquiry.email')),
  }),
)
const topics = computed(() => SUPPORT_TOPICS.map(value => ({ value, label: t(`help.contact.topic.${value}`) })))
const areas = computed(() => [{ value: null, label: t('help.contact.anyArea') }, ...HELP_CATEGORIES.map(value => ({ value, label: t(`help.category.${value}.name`) }))])
const STATUS_COLOR = { open: 'warning', answered: 'success', closed: 'neutral' } as const

const { busy, run } = useBusy()
async function send() {
  await run(async () => {
    const { data } = await api.post<SupportRequest>('/help/support-requests', { ...state.value, page: from.value, article: support.preset.value.article ?? null })
    sent.value = data
    earlier.value = [data, ...(earlier.value ?? [])]
  })
}
</script>

<template>
  <AppModal v-model:open="support.open.value" :title="t('help.contact.title')" :description="t('help.contact.desc')" keep-open :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div v-if="sent" class="flex flex-col gap-4">
        <AppEmpty
          icon="i-lucide-mail-check"
          :title="t('help.contact.sentTitle', { reference: sent.reference })"
          :description="t('help.contact.sentDesc', { email: sent.email })"
          :actions="[{ label: t('help.contact.another'), color: 'neutral', variant: 'outline', onClick: () => ((sent = null), (state = blank())) }, { label: t('billing.enquiry.close'), color: 'neutral', onClick: () => (support.open.value = false) }]"
        />
      </div>
      <UForm v-else id="support-request" :schema="schema" :state="state" class="flex flex-col gap-4" @submit="send">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <UFormField :label="t('help.contact.topicLabel')"><USelect v-model="state.topic" :items="topics" class="w-full" /></UFormField>
          <UFormField :label="t('help.contact.areaLabel')"><USelect v-model="state.area" :items="areas" class="w-full" /></UFormField>
        </div>
        <UFormField name="subject" :label="t('help.contact.subject')" required>
          <UInput v-model="state.subject" :maxlength="140" class="w-full" :placeholder="t('help.contact.subjectPlaceholder')" />
        </UFormField>
        <UFormField name="message" :label="t('help.contact.message')" :help="t('help.contact.messageHelp')" required>
          <UTextarea v-model="state.message" :rows="6" :maxlength="5000" class="w-full" />
        </UFormField>
        <div class="flex items-center gap-3 rounded-lg border border-default p-3">
          <UIcon name="i-lucide-siren" class="size-4 shrink-0 text-muted" />
          <span class="flex min-w-0 flex-1 flex-col"><span class="text-sm text-highlighted">{{ t('help.contact.urgent') }}</span><span class="text-xs text-muted">{{ t('help.contact.urgentHint') }}</span></span>
          <USwitch v-model="state.urgent" color="neutral" :aria-label="t('help.contact.urgent')" />
        </div>
        <UFormField name="email" :label="t('help.contact.replyTo')" required>
          <UInput v-model="state.email" type="email" icon="i-lucide-mail" class="w-full sm:max-w-sm" autocomplete="email" />
        </UFormField>
        <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('help.contact.included') }}</p>
      </UForm>

      <section v-if="earlier?.length" class="mt-5 flex flex-col gap-2 border-t border-default pt-4">
        <h3 class="text-xs font-medium text-muted uppercase">{{ t('help.contact.yours') }}</h3>
        <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
          <li v-for="item in earlier.slice(0, 5)" :key="item.id" class="flex items-center gap-3 px-3 py-2">
            <span class="font-mono text-xs text-muted">{{ item.reference }}</span>
            <span class="min-w-0 flex-1 truncate text-sm text-default">{{ item.subject }}</span>
            <span class="hidden text-xs text-muted sm:inline">{{ relative(item.created_at) }}</span>
            <UBadge :label="t(`help.contact.status.${item.status}`)" :color="STATUS_COLOR[item.status]" variant="subtle" size="sm" />
          </li>
        </ul>
      </section>
    </template>
    <template v-if="!sent" #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="support.open.value = false" />
        <UButton type="submit" form="support-request" :label="t('help.contact.send')" icon="i-lucide-send" color="neutral" :loading="busy" />
      </div>
    </template>
  </AppModal>
</template>
