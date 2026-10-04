<!--
  What a locked public form asks for (F10 M3): the password (PublicUnlock), a personal invitation
  link, or signing in as a member of the organisation. Invitation links and sign-in passes arrive in
  the address (`?invite=` / `?pass=`) and are used automatically by FormView (usePublicAccess).
-->
<script setup lang="ts">
import type { PublicForm } from '#shared/types/public'
import { portalLink, publicHosts } from '#shared/utils/urls/public'

const props = defineProps<{ form: PublicForm; formKey: string; failed: 'invite' | 'pass' | null }>()
defineEmits<{ unlocked: [] }>()
const { t } = useI18n()
const config = useRuntimeConfig().public
const url = useRequestURL()

/** Members sign in on their workspace's portal, which sends them straight back. */
const signIn = computed(() =>
  portalLink(publicHosts(config, url.port), String(config.manageSubdomain), props.form.workspace.subdomain, `/forms/open?key=${encodeURIComponent(props.formKey)}`),
)
</script>

<template>
  <PublicUnlock v-if="form.lock === 'password'" :form-key="formKey" class="mt-2" @unlocked="$emit('unlocked')" />
  <div v-else-if="form.lock === 'invite'" class="mt-1 flex w-full flex-col gap-2 text-start">
    <UAlert v-if="failed === 'invite'" icon="i-lucide-link-2-off" color="warning" variant="subtle" :title="t('public.invite.badLink')" :description="t('public.invite.badLinkDesc')" />
    <p class="flex items-start gap-2 rounded-md bg-elevated/60 p-3 text-xs text-toned">
      <UIcon name="i-lucide-mail" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('public.invite.how') }}
    </p>
  </div>
  <div v-else-if="form.lock === 'organisation'" class="mt-1 flex w-full flex-col gap-2">
    <UAlert v-if="failed === 'pass'" icon="i-lucide-clock-alert" color="warning" variant="subtle" :title="t('errors.FRM-FORM-1019')" />
    <UButton :to="signIn" external :label="t('public.member.signIn', { org: form.workspace.name })" icon="i-lucide-log-in" color="neutral" block />
  </div>
</template>
