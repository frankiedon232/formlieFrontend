<!--
  Beside the endpoint wizard (below on phones): the address as it will be, with Copy, the methods,
  and an example call that follows every choice; a short note on where the data goes.
-->
<script setup lang="ts">
import type { ApiEndpointField } from '#shared/types/apiService'
import type { ApiMethod } from '#shared/utils/urls/public'

defineProps<{ url: string; methods: ApiMethod[]; fields: ApiEndpointField[]; pageSize: number; formName: string; headers?: { name: string; value: string }[] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex min-w-0 flex-col gap-3">
    <div class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-route" class="size-4 shrink-0 text-muted" />
        <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.wizard.preview') }}</h3>
      </div>
      <AppCopyField :value="url" :label="t('apiService.address')" monospace />
      <ApiMethods :methods="methods" all size="xs" />
      <p v-if="formName" class="flex min-w-0 items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-file-text" class="size-3.5 shrink-0" /><span class="truncate">{{ formName }}</span></p>
    </div>
    <div v-if="fields.length && methods.length" class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
      <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.call.title') }}</h3>
      <ApiEndpointsExample :methods="methods" :url="url" :fields="fields" :page-size="pageSize" :headers="headers" />
    </div>
    <div class="flex gap-2 rounded-lg border border-dashed border-default p-3 text-xs text-muted">
      <UIcon name="i-lucide-database" class="mt-0.5 size-3.5 shrink-0" />
      <span>{{ t('apiService.wizard.where') }}</span>
    </div>
  </div>
</template>
