<!--
  Endpoint wizard, step 3 (F13 M1): which of GET, POST, PUT and DELETE the endpoint answers (only
  these four for now), each with what it does; GET also sets the largest page it returns.
-->
<script setup lang="ts">
import { API_PAGE_SIZE_MAX } from '#shared/utils/apiService/endpoints'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'

defineProps<{ error?: string }>()
const methods = defineModel<ApiMethod[]>('methods', { required: true })
const pageSize = defineModel<number>('pageSize', { required: true })
const { t } = useI18n()
const ICONS: Record<ApiMethod, string> = { GET: 'i-lucide-arrow-up-from-line', POST: 'i-lucide-arrow-down-to-line', PUT: 'i-lucide-pencil-line', DELETE: 'i-lucide-trash-2' }
const toggle = (method: ApiMethod) => (methods.value = methods.value.includes(method) ? methods.value.filter(item => item !== method) : API_METHODS.filter(item => item === method || methods.value.includes(item)))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div role="group" :aria-label="t('apiService.wizard.step.methods')" class="grid gap-2 sm:grid-cols-2">
      <button
        v-for="method in API_METHODS"
        :key="method"
        type="button"
        role="checkbox"
        :aria-checked="methods.includes(method)"
        class="flex items-start gap-3 rounded-lg border p-3 text-start transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="methods.includes(method) ? 'border-(--ui-border-inverted) bg-elevated/60 ring-1 ring-(--ui-border-inverted)' : 'border-default hover:border-accented hover:bg-elevated/40'"
        @click="toggle(method)"
      >
        <span class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-default"><UIcon :name="ICONS[method]" class="size-4 text-highlighted" /></span>
        <span class="flex min-w-0 flex-1 flex-col gap-0.5">
          <span class="font-mono text-sm font-semibold text-highlighted">{{ method }}</span>
          <span class="text-xs text-muted">{{ t(`apiService.wizard.method.${method}`) }}</span>
        </span>
        <UCheckbox :model-value="methods.includes(method)" color="neutral" tabindex="-1" aria-hidden="true" class="pointer-events-none" />
      </button>
    </div>
    <p v-if="error" class="text-sm text-error">{{ error }}</p>
    <UFormField v-if="methods.includes('GET')" :label="t('apiService.pageSize')" :help="t('apiService.wizard.pageSizeHelp', { max: API_PAGE_SIZE_MAX })">
      <UInputNumber v-model="pageSize" :min="1" :max="API_PAGE_SIZE_MAX" class="w-36" />
    </UFormField>
  </div>
</template>
