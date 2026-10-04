<!-- Step 4, invite teammates (optional). Paste a list into any row to split it into rows. -->
<script setup lang="ts">
import { z } from 'zod'
import type { OnboardingInvite } from '#shared/types/onboarding'

const invites = defineModel<OnboardingInvite[]>({ required: true })
const emit = defineEmits<{ submit: [] }>()
const { t } = useI18n()
const session = useSession()

const MAX = 20
const roles = computed(() => [
  { value: 'member', label: t('onboarding.team.member') },
  { value: 'admin', label: t('onboarding.team.admin') },
])

const own = computed(() => session.user.value?.email.toLowerCase() ?? '')
const schema = z.object({
  invites: z.array(
    z.object({
      email: z
        .string()
        .trim()
        .refine(value => !value || z.email().safeParse(value).success, t('onboarding.team.invalid'))
        .refine(value => value.toLowerCase() !== own.value, t('onboarding.team.self')),
      role: z.enum(['admin', 'member']),
    }),
  ),
})
// Duplicates are checked across rows (zod per-row cannot see the others).
const duplicate = computed(() => {
  const seen = new Set<string>()
  for (const [index, invite] of invites.value.entries()) {
    const email = invite.email.trim().toLowerCase()
    if (!email) continue
    if (seen.has(email)) return index
    seen.add(email)
  }
  return -1
})

function add() {
  if (invites.value.length < MAX) invites.value.push({ email: '', role: 'member' })
}
function remove(index: number) {
  invites.value.splice(index, 1)
  if (!invites.value.length) add()
}

function onPaste(index: number, event: ClipboardEvent) {
  const emails = (event.clipboardData?.getData('text') ?? '').split(/[\s,;]+/).filter(Boolean)
  if (emails.length < 2) return
  event.preventDefault()
  const rows = emails.slice(0, MAX).map(email => ({ email, role: invites.value[index]?.role ?? 'member' }))
  invites.value.splice(index, 1, ...rows)
  invites.value.splice(MAX)
}

function submit() {
  if (duplicate.value === -1) emit('submit')
}
</script>

<template>
  <UForm
    id="onboarding-step"
    :schema="schema"
    :state="{ invites }"
    class="flex flex-col gap-3"
    @submit="submit"
  >
    <div v-for="(invite, index) in invites" :key="index" class="flex items-start gap-2">
      <UFormField
        :name="`invites.${index}.email`"
        :error="duplicate === index ? t('onboarding.team.duplicate') : undefined"
        class="min-w-0 flex-1"
      >
        <UInput
          v-model="invite.email"
          type="email"
          inputmode="email"
          autocomplete="off"
          :placeholder="t('onboarding.team.placeholder')"
          :aria-label="t('onboarding.team.emailLabel', { n: index + 1 })"
          icon="i-lucide-mail"
          class="w-full"
          @paste="onPaste(index, $event)"
        />
      </UFormField>
      <USelect
        v-model="invite.role"
        :items="roles"
        value-key="value"
        :aria-label="t('onboarding.team.roleLabel', { n: index + 1 })"
        class="w-32 shrink-0"
      />
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="ghost"
        :aria-label="t('onboarding.team.remove', { n: index + 1 })"
        @click="remove(index)"
      />
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <UButton
        :label="t('onboarding.team.add')"
        icon="i-lucide-plus"
        color="neutral"
        variant="outline"
        size="sm"
        :disabled="invites.length >= MAX"
        @click="add"
      />
      <p class="text-xs text-muted">{{ t('onboarding.team.pasteHint') }}</p>
    </div>

    <UAlert
      icon="i-lucide-info"
      color="neutral"
      variant="subtle"
      :description="t('onboarding.team.rolesHint')"
      class="mt-2"
    />
  </UForm>
</template>
