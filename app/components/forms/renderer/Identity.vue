<!--
  Telling respondents apart, on the public form (F10, owner 2026-10-03):
    possible — "This looks like a response we already have (sa•••@yahoo.com, 3 Oct). Is this a
               different person?" Yes → sent, flagged for the team; No → back to the answers.
    verify   — a 6-digit code to the respondent's own email before the form is sent.
  Only a masked hint of an earlier response is ever shown — never its details.
-->
<script setup lang="ts">
import type { RendererRespondent } from '#shared/types/public'

const props = defineProps<{
  reason: 'possible' | 'verify' | null
  hint?: { at?: string; email?: string }
  /** The respondent's email answer (for the code step). */
  email: string
  respondent: Pick<RendererRespondent, 'confirmDifferent' | 'sendCode' | 'confirmCode'>
}>()
const emit = defineEmits<{ continue: []; cancel: [] }>()
const { t } = useI18n()
const { date } = useFormat()

const open = computed({
  get: () => !!props.reason,
  set: value => !value && emit('cancel'),
})

// ── Possible duplicate ───────────────────────────────────────────────────────────────
function different() {
  props.respondent.confirmDifferent()
  emit('continue')
}

// ── Email code ───────────────────────────────────────────────────────────────────────
const digits = ref<number[]>([])
const sentTo = ref('')
const devCode = ref<string | null>(null)
const { busy: sending, run: runSend } = useBusy()
const { busy: checking, run: runCheck } = useBusy()
async function send() {
  await runSend(async () => {
    const sent = await props.respondent.sendCode(props.email)
    if (sent) {
      sentTo.value = sent.sentTo
      devCode.value = sent.devCode
      digits.value = []
    }
  })
}
watch(
  () => props.reason,
  reason => {
    if (reason === 'verify') void send()
  },
)
async function check(code = digits.value.join('')) {
  if (code.length !== 6) return
  await runCheck(async () => {
    if (await props.respondent.confirmCode(props.email, code)) emit('continue')
    else digits.value = []
  })
}
const showDevCode = computed(() => import.meta.dev && !!devCode.value)
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="reason === 'verify' ? t('renderer.identity.verifyTitle') : t('renderer.identity.possibleTitle')"
    :description="
      reason === 'verify'
        ? t('renderer.identity.verifyDesc', { email: sentTo || hint?.email || '' })
        : t('renderer.identity.possibleDesc', { email: hint?.email || '—', date: hint?.at ? date(hint.at, 'long') : '—' })
    "
    :dismissible="!checking"
  >
    <template #body>
      <ul v-if="reason === 'possible'" class="flex flex-col gap-2 text-sm text-default">
        <li class="flex items-start gap-2"><UIcon name="i-lucide-user-round-check" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('renderer.identity.possiblePoint1') }}</li>
        <li class="flex items-start gap-2"><UIcon name="i-lucide-pencil-line" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('renderer.identity.possiblePoint2') }}</li>
      </ul>
      <div v-else class="flex flex-col items-center gap-3">
        <UPinInput
          v-model="digits"
          :length="6"
          otp
          type="number"
          size="xl"
          :disabled="checking || sending"
          :aria-label="t('renderer.identity.codeLabel')"
          @complete="v => check(v.join(''))"
        />
        <p v-if="showDevCode" class="text-xs text-muted">{{ t('auth.otp.devCode', { code: devCode }) }}</p>
        <UButton :label="t('renderer.identity.resend')" icon="i-lucide-rotate-cw" color="neutral" variant="link" size="sm" :loading="sending" @click="send" />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <template v-if="reason === 'possible'">
          <UButton :label="t('renderer.identity.review')" color="neutral" variant="outline" class="justify-center" @click="emit('cancel')" />
          <UButton :label="t('renderer.identity.different')" icon="i-lucide-user-plus" color="neutral" class="justify-center" @click="different" />
        </template>
        <template v-else>
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" class="justify-center" :disabled="checking" @click="emit('cancel')" />
          <UButton :label="t('renderer.identity.confirm')" icon="i-lucide-shield-check" color="neutral" class="justify-center" :loading="checking" :disabled="digits.join('').length !== 6" @click="check()" />
        </template>
      </div>
    </template>
  </AppModal>
</template>
