<!-- My profile → Email notifications (F16 M5): which emails this person wants; security emails always go out. -->
<script setup lang="ts">
import { PROFILE_NOTIFICATIONS, type MyProfile, type ProfileNotification } from '#shared/types/profile'

const props = defineProps<{ profile: MyProfile; saving: string | null }>()
const emit = defineEmits<{ save: [part: string, values: Partial<MyProfile>] }>()
const { t } = useI18n()
const toggle = (key: ProfileNotification, value: boolean) => emit('save', `notify-${key}`, { notifications: { ...props.profile.notifications, [key]: value } })
</script>

<template>
  <SettingsBlock :title="t('profile.notify.title')" :description="t('profile.notify.desc')" icon="i-lucide-bell">
    <div class="flex flex-col gap-3">
      <USwitch v-for="key in PROFILE_NOTIFICATIONS" :key="key" :model-value="profile.notifications[key]" :label="t(`profile.notify.${key}`)" :description="t(`profile.notify.${key}Hint`)" color="neutral" :loading="saving === `notify-${key}`" :disabled="!!saving" @update:model-value="value => toggle(key, !!value)" />
      <USwitch :model-value="true" disabled :label="t('profile.notify.security')" :description="t('profile.notify.securityHint')" color="neutral" />
    </div>
  </SettingsBlock>
</template>
