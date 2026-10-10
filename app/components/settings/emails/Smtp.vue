<!--
  Settings → Emails → Sending address → Your own mail server: host, port, security, sign-in and the from address.
  The password is write-only (a saved one shows as set; typing replaces it). Test connects to the server before it
  can be used; a changed server needs a new test.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { EmailSending, SmtpServer } from '#shared/types/emails'

const props = defineProps<{ server: SmtpServer | null }>()
const emit = defineEmits<{ saved: [value: EmailSending] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const confirm = useConfirm()

const blank = () => ({ host: '', port: 587, security: 'starttls' as SmtpServer['security'], username: '', password: '', from_address: '' })
const draft = ref(blank())
const editing = ref(false)
function edit() {
  const server = props.server
  draft.value = server ? { host: server.host, port: server.port, security: server.security, username: server.username ?? '', password: '', from_address: server.from_address } : blank()
  editing.value = true
}

const schema = z.object({
  host: z.string().trim().min(1, t('settings.smtp.hostRequired')),
  port: z.number().int().min(1).max(65535),
  security: z.enum(['starttls', 'tls', 'none']),
  username: z.string().max(200),
  password: z.string().max(500),
  from_address: z.email(t('settings.smtp.fromInvalid')),
})
const securities = computed(() => (['starttls', 'tls', 'none'] as const).map(value => ({ value, label: t(`settings.smtp.security.${value}`) })))
// The usual port for each kind of security
watch(
  () => draft.value.security,
  (security, before) => {
    const usual = { starttls: 587, tls: 465, none: 25 }
    if (before && draft.value.port === usual[before]) draft.value.port = usual[security]
  },
)

const { busy, run } = useBusy()
async function save() {
  const value = draft.value
  const ok = await run(async () => {
    const body = { host: value.host.trim(), port: value.port, security: value.security, username: value.username.trim() || null, from_address: value.from_address.trim(), ...(value.password ? { password: value.password } : {}) }
    emit('saved', (await api.put<EmailSending>('/settings/emails/sending/smtp', body)).data)
    return true
  })
  if (ok) {
    editing.value = false
    toast.add({ title: t('settings.smtp.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  }
}

const testing = ref(false)
async function test() {
  if (testing.value) return
  testing.value = true
  try {
    const result = (await api.post<EmailSending>('/settings/emails/sending/smtp/test')).data
    emit('saved', result)
    const working = result.smtp?.status === 'working'
    toast.add({ title: working ? t('settings.smtp.working') : t(`settings.smtp.problem.${result.smtp?.problem ?? 'unreachable'}`), color: working ? 'success' : 'error', icon: working ? 'i-lucide-plug-zap' : 'i-lucide-unplug' })
  } catch (error) {
    handle(error)
  } finally {
    testing.value = false
  }
}

async function remove() {
  if (!props.server || !(await confirm({ title: t('settings.smtp.removeTitle', { host: props.server.host }), description: t('settings.sending.removeDesc'), confirmLabel: t('settings.smtp.remove'), danger: true }))) return
  await run(async () => emit('saved', (await api.del<EmailSending>('/settings/emails/sending/smtp')).data))
}
const STATUS_COLOR = { untested: 'neutral', working: 'success', failed: 'error' } as const
</script>

<template>
  <div class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
    <h3 class="flex items-center gap-2 text-sm font-medium text-highlighted"><UIcon name="i-lucide-server" class="size-4 text-muted" />{{ t('settings.sending.smtp') }}</h3>

    <UForm v-if="editing" :schema="schema" :state="draft" class="flex flex-col gap-4" @submit="save">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_7rem]">
        <UFormField name="host" :label="t('settings.smtp.host')" required>
          <UInput v-model="draft.host" placeholder="smtp.example.com" icon="i-lucide-server" class="w-full" autocomplete="off" />
        </UFormField>
        <UFormField name="port" :label="t('settings.smtp.port')" required>
          <UInputNumber v-model="draft.port" :min="1" :max="65535" :format-options="{ useGrouping: false }" class="w-full" />
        </UFormField>
      </div>
      <UFormField name="security" :label="t('settings.smtp.securityLabel')">
        <USelect v-model="draft.security" :items="securities" class="w-full sm:max-w-sm" />
      </UFormField>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UFormField name="username" :label="t('settings.smtp.username')">
          <UInput v-model="draft.username" icon="i-lucide-user-round" class="w-full" autocomplete="off" />
        </UFormField>
        <UFormField name="password" :label="t('settings.smtp.password')" :help="server?.has_password ? t('settings.smtp.passwordKept') : undefined">
          <UInput v-model="draft.password" type="password" icon="i-lucide-key-round" :placeholder="server?.has_password ? '••••••••' : ''" class="w-full" autocomplete="new-password" />
        </UFormField>
      </div>
      <UFormField name="from_address" :label="t('settings.smtp.from')" :help="t('settings.smtp.fromHelp')" required>
        <UInput v-model="draft.from_address" type="email" icon="i-lucide-mail" placeholder="forms@example.com" class="w-full sm:max-w-sm" />
      </UFormField>
      <div class="flex flex-wrap gap-2">
        <UButton type="submit" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" />
        <UButton :label="t('common.cancel')" color="neutral" variant="ghost" :disabled="busy" @click="editing = false" />
      </div>
    </UForm>

    <template v-else-if="server">
      <div class="flex flex-wrap items-center gap-2">
        <span class="font-mono text-sm text-highlighted">{{ server.host }}:{{ server.port }}</span>
        <UBadge :label="t(`settings.smtp.status.${server.status}`)" :color="STATUS_COLOR[server.status]" variant="subtle" />
        <span v-if="server.checked_at" class="text-xs text-muted">{{ t('settings.address.checked', { when: relative(server.checked_at) }) }}</span>
      </div>
      <p class="text-xs text-muted">{{ t('settings.smtp.summary', { from: server.from_address, security: t(`settings.smtp.security.${server.security}`) }) }}</p>
      <UAlert v-if="server.problem" color="error" variant="subtle" icon="i-lucide-unplug" :description="t(`settings.smtp.problem.${server.problem}`)" />
      <div class="flex flex-wrap gap-2">
        <UButton :label="t('settings.smtp.test')" icon="i-lucide-plug-zap" color="neutral" :loading="testing" @click="test" />
        <UButton :label="t('settings.smtp.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" :disabled="busy" @click="edit" />
        <UButton :label="t('settings.smtp.remove')" icon="i-lucide-trash-2" color="error" variant="outline" :disabled="busy" @click="remove" />
      </div>
    </template>

    <div v-else class="flex flex-col items-start gap-2">
      <p class="text-xs text-muted">{{ t('settings.smtp.intro') }}</p>
      <UButton :label="t('settings.smtp.add')" icon="i-lucide-plus" color="neutral" variant="outline" @click="edit" />
    </div>
  </div>
</template>
