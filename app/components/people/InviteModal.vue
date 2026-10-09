<!--
  Invite people (F16 M2): one or many email addresses (typed, or pasted from a list), their role, and
  the departments and job titles they belong to, set at once; an optional note for the email. Each gets
  the workspace's invitation email with a link that works for 7 days. Addresses already in the workspace
  or already invited are left out and named.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { Directory } from '#shared/types/directory'
import type { InviteRequest, InviteResult } from '#shared/types/people'

const open = defineModel<boolean>('open', { default: false })
const props = defineProps<{ directory: Directory | null }>()
const emit = defineEmits<{ invited: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { number } = useFormat()

const blank = (): InviteRequest & { message: string } => ({ emails: [], role: 'member', department_ids: [], job_title_ids: [], message: '' })
const state = ref(blank())
watch(open, value => value && (state.value = blank()))

// A pasted list ("a@x.org, b@y.org; c@z.org") becomes one address per tag
watch(
  () => state.value.emails,
  emails => {
    const split = [...new Set(emails.flatMap(item => item.split(/[\s,;]+/)).map(item => item.trim()).filter(Boolean))]
    if (split.join('|') !== emails.join('|')) state.value.emails = split
  },
  { deep: true },
)
const isEmail = (value: string) => z.email().safeParse(value).success
const wrong = computed(() => state.value.emails.filter(item => !isEmail(item)))
const tooMany = computed(() => state.value.emails.length > 50)
const canSend = computed(() => state.value.emails.length > 0 && !wrong.value.length && !tooMany.value)

const roles = computed(() => [
  { value: 'member', label: t('people.role.member'), description: t('people.invite.memberHint') },
  { value: 'admin', label: t('people.role.admin'), description: t('people.invite.adminHint') },
])
const departments = computed(() => (props.directory?.departments ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))
const jobTitles = computed(() => (props.directory?.job_titles ?? []).filter(item => !item.archived).map(item => ({ value: item.id, label: item.name })))

const sending = ref(false)
async function send() {
  if (!canSend.value || sending.value) return
  sending.value = true
  try {
    const { data } = await api.post<InviteResult>('/people/invites', { ...state.value, message: state.value.message?.trim() || null })
    const skipped = data.skipped.map(item => `${item.email} (${t(`people.invite.skip.${item.reason}`)})`).join(', ')
    toast.add({
      title: data.invited ? t('people.invite.sent', { n: number(data.invited) }, data.invited) : t('people.invite.noneSent'),
      description: skipped ? t('people.invite.skipped', { list: skipped }) : undefined,
      color: data.invited ? 'success' : 'warning',
      icon: data.invited ? 'i-lucide-mail-check' : 'i-lucide-triangle-alert',
    })
    if (data.invited) {
      open.value = false
      emit('invited')
    }
  } catch (error) {
    handle(error)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('people.invite.title')" :description="t('people.invite.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="send">
        <UFormField :label="t('people.invite.emails')" :description="t('people.invite.emailsHint')" required :error="wrong.length ? t('people.invite.wrong', { list: wrong.join(', ') }) : tooMany ? t('people.invite.tooMany') : undefined">
          <UInputTags v-model="state.emails" :placeholder="t('people.invite.emailsPlaceholder')" icon="i-lucide-at-sign" :add-on-blur="true" :add-on-paste="true" class="w-full" autofocus />
        </UFormField>
        <UFormField :label="t('people.col.role')">
          <URadioGroup v-model="state.role" :items="roles" value-key="value" color="neutral" variant="card" orientation="horizontal" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('people.col.departments')">
            <USelectMenu v-model="state.department_ids" :items="departments" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-building-2" class="w-full" />
            <template v-if="!departments.length" #hint><NuxtLink to="/settings/departments" class="underline">{{ t('people.invite.addDepartments') }}</NuxtLink></template>
          </UFormField>
          <UFormField :label="t('people.col.jobTitles')">
            <USelectMenu v-model="state.job_title_ids" :items="jobTitles" value-key="value" multiple :placeholder="t('people.invite.pick')" icon="i-lucide-briefcase" class="w-full" />
            <template v-if="!jobTitles.length" #hint><NuxtLink to="/settings/job-titles" class="underline">{{ t('people.invite.addJobTitles') }}</NuxtLink></template>
          </UFormField>
        </div>
        <UFormField :label="t('people.invite.message')" :hint="t('people.invite.optional')">
          <UTextarea v-model="state.message" :rows="2" maxlength="500" :placeholder="t('people.invite.messagePlaceholder')" class="w-full" />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <span class="text-xs text-muted">{{ t('people.invite.expires') }}</span>
        <div class="flex gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="state.emails.length > 1 ? t('people.invite.sendMany', { n: state.emails.length }) : t('people.invite.send')" icon="i-lucide-send" color="neutral" :loading="sending" :disabled="!canSend" @click="send" />
        </div>
      </div>
    </template>
  </AppModal>
</template>
