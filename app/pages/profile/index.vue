<!--
  My profile (F16 M5): every person, about themselves: details and photo, language and region, their
  place in the workspace (set by admins), password, two-step sign-in (authenticator app with recovery
  codes, SMS number), where they are signed in, and which emails they get.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'user.profile' })
const { t } = useI18n()
useHead({ title: () => t('user.profile') })
const { profile, failed, saving, load, save } = useProfile()
onMounted(load)
const sessions = useTemplateRef<{ reload: () => void }>('sessions')
const changedPassword = () => Promise.all([load(), sessions.value?.reload()])
</script>

<template>
  <AppPanel id="profile" :title="t('user.profile')" :subtitle="t('profile.subtitle')">
    <AppEmpty v-if="failed" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: load }]" />
    <div v-else-if="!profile" class="flex flex-col gap-6"><USkeleton v-for="n in 4" :key="n" class="h-32 rounded-lg" /></div>
    <div v-else class="flex max-w-5xl flex-col gap-6">
      <ProfileDetails :profile="profile" :saving="saving" @save="save" />
      <ProfilePreferences :profile="profile" :saving="saving" @save="save" />
      <ProfilePlace :profile="profile" />
      <ProfilePassword :changed-at="profile.password_changed_at" @changed="changedPassword" />
      <ProfileTwoStep :profile="profile" @changed="load" />
      <ProfileSessions ref="sessions" />
      <ProfileNotifications :profile="profile" :saving="saving" @save="save" />
      <ProfileTips />
    </div>
  </AppPanel>
</template>
