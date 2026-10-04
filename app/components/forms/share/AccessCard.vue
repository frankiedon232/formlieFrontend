<!--
  Share → Access (F10 M3): anyone with the link, or only people who know the password. A password
  is set or changed here (8+ characters, never shown again — stored as a hash); changing it means
  everyone has to enter the new one. Invite-only and organisation-only come later in M3.
-->
<script setup lang="ts">
import type { FormShareSettings, ShareDraft } from '#shared/types/forms'

defineProps<{ settings: FormShareSettings }>()
const draft = defineModel<ShareDraft>('draft', { required: true })
const { t } = useI18n()
const { relative } = useFormat()

const items = computed(() => [
  { value: 'public', label: t('share.access.public'), description: t('share.access.publicDesc') },
  { value: 'password', label: t('share.access.password'), description: t('share.access.passwordDesc') },
])
const changing = ref(false)
const show = ref(false)
watch(
  () => draft.value.password,
  value => !value && (changing.value = false),
)
const tooShort = computed(() => !!draft.value.password && draft.value.password.length < 8)
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start gap-3">
      <UIcon name="i-lucide-shield" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.access.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.access.desc') }}</p>
      </div>
    </div>
    <URadioGroup v-model="draft.access" :items="items" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" :aria-label="t('share.access.title')" />

    <div v-if="draft.access === 'password'" class="mt-4 flex flex-col gap-2 rounded-md border border-default bg-elevated/40 p-3">
      <div v-if="settings.has_password && !changing" class="flex flex-wrap items-center justify-between gap-2">
        <span class="flex items-center gap-2 text-sm text-highlighted">
          <UIcon name="i-lucide-key-round" class="size-4 text-success" />
          {{ settings.password_changed_at ? t('share.access.passwordSetOn', { when: relative(settings.password_changed_at) }) : t('share.access.passwordSet') }}
        </span>
        <UButton :label="t('share.access.change')" icon="i-lucide-pencil" color="neutral" variant="outline" size="xs" @click="changing = true" />
      </div>
      <UFormField
        v-else
        :label="settings.has_password ? t('share.access.newPassword') : t('share.access.setPassword')"
        :description="t('share.access.passwordHint')"
        :error="tooShort ? t('share.access.tooShort') : undefined"
      >
        <UInput v-model="draft.password" :type="show ? 'text' : 'password'" autocomplete="new-password" icon="i-lucide-key-round" class="w-full" :ui="{ trailing: 'pe-1' }">
          <template #trailing>
            <UButton :icon="show ? 'i-lucide-eye-off' : 'i-lucide-eye'" :aria-label="show ? t('public.locked.hide') : t('public.locked.show')" color="neutral" variant="link" size="sm" @click="show = !show" />
          </template>
        </UInput>
      </UFormField>
      <p class="text-xs text-muted">{{ t('share.access.passwordNote') }}</p>
    </div>
  </UCard>
</template>
