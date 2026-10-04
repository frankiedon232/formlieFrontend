<!--
  Share → Invite-only → the invitations (F10 M3, decision 96). Type or paste emails only (owner):
  each becomes a chip on comma, space, semicolon or Enter; invalid ones are red and block sending
  (FormsShareEmailChips) → each person gets a personal link (emailed by the
  backend; in development the links are shown to copy). Each person can respond once; their status
  shows Invited · Opened · Responded. Resend gives a new link (the old one stops working); Revoke
  stops it. Changes apply at once (separate from the page's Save).
-->
<script setup lang="ts">
import type { EmailChip, FormInvitation } from '#shared/types/forms'

const props = defineProps<{ formId: string; saved: boolean }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const { copy } = useClipboard({ legacy: true })

const invitations = ref<FormInvitation[]>([])
const loading = ref(true)
async function load() {
  loading.value = true
  try {
    invitations.value = (await api.get<FormInvitation[]>(`/forms/${props.formId}/invites`)).data
  } catch (error) {
    handle(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

// Emails only (owner): each address is a chip; invalid ones are red and block sending.
const chips = ref<EmailChip[]>([])
const valid = computed(() => chips.value.filter(chip => chip.valid).map(chip => chip.value))
const invalidCount = computed(() => chips.value.filter(chip => !chip.valid).length)

/** Personal links just created / resent (development: the backend emails them in production). */
const links = ref<{ email: string; url: string }[]>([])
const { busy, run } = useBusy()
async function invite() {
  if (!valid.value.length || invalidCount.value) return
  await run(async () => {
    try {
      const reply = await api.post<{ invitations: FormInvitation[]; created: number; skipped: string[] }>(`/forms/${props.formId}/invites`, { people: valid.value.map(email => ({ email })) })
      invitations.value = reply.data.invitations
      links.value = (reply.meta?.dev_links as typeof links.value | undefined) ?? []
      chips.value = []
      toast.add({
        title: t('share.invite.sent', { n: reply.data.created }, reply.data.created),
        description: reply.data.skipped.length ? t('share.invite.skipped', { n: reply.data.skipped.length }, reply.data.skipped.length) : undefined,
        icon: 'i-lucide-send',
        color: 'success',
      })
    } catch (error) {
      handle(error)
    }
  })
}

const working = ref<string | null>(null)
async function resend(item: FormInvitation) {
  working.value = item.id
  try {
    const reply = await api.post<{ invitations: FormInvitation[] }>(`/forms/${props.formId}/invites/${item.id}/resend`)
    invitations.value = reply.data.invitations
    links.value = (reply.meta?.dev_links as typeof links.value | undefined) ?? []
    toast.add({ title: t('share.invite.resent', { email: item.email }), icon: 'i-lucide-send', color: 'success' })
  } catch (error) {
    handle(error)
  } finally {
    working.value = null
  }
}
async function revoke(item: FormInvitation) {
  if (!(await confirm({ title: t('share.invite.revokeTitle', { email: item.email }), description: t('share.invite.revokeDesc'), confirmLabel: t('share.invite.revoke'), danger: true }))) return
  working.value = item.id
  try {
    invitations.value = (await api.del<{ invitations: FormInvitation[] }>(`/forms/${props.formId}/invites/${item.id}`)).data.invitations
  } catch (error) {
    handle(error)
  } finally {
    working.value = null
  }
}
/** A revoked invitation off the list (a response they already sent is kept). */
async function removeRevoked(item: FormInvitation) {
  working.value = item.id
  try {
    invitations.value = (await api.del<{ invitations: FormInvitation[] }>(`/forms/${props.formId}/invites/${item.id}`, { query: { remove: '1' } })).data.invitations
    toast.add({ title: t('share.invite.removed', { email: item.email }), icon: 'i-lucide-check', color: 'success' })
  } catch (error) {
    handle(error)
  } finally {
    working.value = null
  }
}
function copyLink(url: string) {
  copy(url)
  toast.add({ title: t('share.link.copied'), icon: 'i-lucide-check', color: 'success' })
}

const STATUS: Record<FormInvitation['status'], { color: 'neutral' | 'info' | 'success' | 'error'; icon: string }> = {
  invited: { color: 'neutral', icon: 'i-lucide-mail' },
  opened: { color: 'info', icon: 'i-lucide-mail-open' },
  responded: { color: 'success', icon: 'i-lucide-circle-check' },
  revoked: { color: 'error', icon: 'i-lucide-ban' },
}
const counts = computed(() => ({
  total: invitations.value.filter(item => item.status !== 'revoked').length,
  responded: invitations.value.filter(item => item.status === 'responded').length,
}))
</script>

<template>
  <div class="flex flex-col gap-3 rounded-md border border-default bg-elevated/40 p-3">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-sm font-medium text-highlighted">{{ t('share.invite.title') }}</span>
      <span v-if="counts.total" class="text-xs text-muted tabular-nums">{{ t('share.invite.counts', { responded: counts.responded, total: counts.total }) }}</span>
    </div>
    <UAlert v-if="!saved" icon="i-lucide-info" color="neutral" variant="subtle" :title="t('share.invite.saveFirst')" />

    <UFormField :label="t('share.invite.add')" :description="t('share.invite.addHint')" :error="invalidCount ? t('share.invite.fixRed', { n: invalidCount }, invalidCount) : undefined">
      <FormsShareEmailChips v-model="chips" :placeholder="t('share.invite.placeholder')" :disabled="busy" />
    </UFormField>
    <div class="flex justify-end">
      <UButton
        :label="valid.length ? t('share.invite.button', { n: valid.length }, valid.length) : t('share.invite.buttonEmpty')"
        icon="i-lucide-send"
        color="neutral"
        size="sm"
        :loading="busy"
        :disabled="!valid.length || invalidCount > 0"
        @click="invite"
      />
    </div>

    <!-- Development: the personal links that would be emailed. -->
    <div v-if="links.length" class="flex flex-col gap-1.5 rounded-md border border-dashed border-default p-2">
      <span class="text-xs text-muted">{{ t('share.invite.devLinks') }}</span>
      <div v-for="link in links" :key="link.url" class="flex items-center gap-2">
        <span class="w-36 shrink-0 truncate text-xs text-highlighted">{{ link.email }}</span>
        <code class="min-w-0 flex-1 truncate text-[11px] text-muted" dir="ltr">{{ link.url }}</code>
        <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" :aria-label="t('share.link.copy')" @click="copyLink(link.url)" />
      </div>
    </div>

    <div v-if="loading" class="flex flex-col gap-2"><USkeleton v-for="n in 2" :key="n" class="h-10 w-full" /></div>
    <p v-else-if="!invitations.length" class="text-xs text-muted">{{ t('share.invite.none') }}</p>
    <ul v-else class="flex max-h-72 flex-col divide-y divide-default overflow-y-auto rounded-md border border-default bg-default">
      <li v-for="item in invitations" :key="item.id" class="flex flex-wrap items-center gap-2 px-3 py-2" :class="working === item.id ? 'opacity-60' : ''">
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-highlighted">{{ item.name || item.email }}</p>
          <p class="truncate text-xs text-muted">
            <template v-if="item.name">{{ item.email }} · </template>{{ t(`share.invite.when.${item.status}`, { when: relative(item.responded_at ?? item.opened_at ?? item.sent_at) }) }}
          </p>
        </div>
        <UBadge :label="t(`share.invite.status.${item.status}`)" :color="STATUS[item.status].color" :icon="STATUS[item.status].icon" variant="subtle" size="sm" />
        <div v-if="item.status !== 'revoked'" class="flex gap-1">
          <UButton v-if="item.status !== 'responded'" icon="i-lucide-rotate-cw" color="neutral" variant="ghost" size="xs" :loading="working === item.id" :aria-label="t('share.invite.resend')" @click="resend(item)" />
          <UButton icon="i-lucide-ban" color="neutral" variant="ghost" size="xs" :disabled="working === item.id" :aria-label="t('share.invite.revoke')" @click="revoke(item)" />
        </div>
        <UTooltip v-else :text="t('share.invite.remove')">
          <UButton icon="i-lucide-trash-2" color="neutral" variant="ghost" size="xs" :loading="working === item.id" :aria-label="t('share.invite.remove')" @click="removeRevoked(item)" />
        </UTooltip>
      </li>
    </ul>
  </div>
</template>
