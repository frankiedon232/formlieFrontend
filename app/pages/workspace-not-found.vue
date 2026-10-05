<!-- Unknown, reserved or suspended workspace host (01.tenant.global.ts). Links to the manage entry. -->
<script setup lang="ts">
definePageMeta({ layout: 'auth', auth: false, manage: true })

const { t } = useI18n()
const route = useRoute()
const tenant = useTenant()
const host = import.meta.client ? location.hostname : ''
const suspended = computed(() => route.query.reason === 'suspended')

useHead({ title: () => (suspended.value ? t('errors.FRM-TEN-1002') : t('error.workspaceTitle')) })
</script>

<template>
  <AppEmpty
    :icon="suspended ? 'i-lucide-pause-circle' : 'i-lucide-building-2'"
    :title="suspended ? t('errors.FRM-TEN-1002') : t('error.workspaceTitle')"
    :description="suspended ? t('error.workspaceSuspendedDesc') : t('error.workspaceDesc', { host })"
    :actions="[
      {
        label: t('error.findWorkspace'),
        icon: 'i-lucide-search',
        to: tenant.manageUrl('/auth/login'),
        external: true,
        color: 'neutral',
      },
    ]"
    variant="naked"
  />
</template>
