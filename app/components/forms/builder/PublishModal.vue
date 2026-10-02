<!--
  Publish (FRONTEND-SPEC §6): optional change summary; blocking issues listed (click → select the
  field). Publishing makes the current draft live; editing later starts a new draft while this
  version stays live.
-->
<script setup lang="ts">
import { publishIssues } from '#shared/utils/forms/build'

const props = defineProps<{ busy: boolean; republish: boolean }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ publish: [summary: string | null] }>()
const { t } = useI18n()
const builder = useBuilder()

const summary = ref('')
watch(open, value => {
  if (value) summary.value = ''
})
const issues = computed(() => (builder.schema.value ? publishIssues(builder.schema.value) : []))
const labelOf = (id: string | null) => {
  const field = id ? builder.findField(id)?.field : null
  return field ? field.label || t(`builder.field.${field.type}`) : null
}
function goTo(id: string | null) {
  if (!id) return
  const found = builder.findField(id)
  if (!found) return
  builder.pageId.value = found.page.id
  builder.select(id)
  open.value = false
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="props.republish ? t('builder.publish.titleAgain') : t('builder.publish.title')"
    :description="props.republish ? t('builder.publish.descAgain') : t('builder.publish.desc')"
    :dismissible="!props.busy"
  >
    <template #body>
      <div v-if="issues.length" class="flex flex-col gap-2">
        <UAlert
          icon="i-lucide-triangle-alert"
          color="warning"
          variant="subtle"
          :title="t('builder.publish.issues', { count: issues.length }, issues.length)"
        />
        <ul class="divide-y divide-default rounded-lg border border-default">
          <li v-for="(issue, index) in issues" :key="index">
            <UButton
              color="neutral"
              variant="ghost"
              class="w-full justify-start rounded-none px-3 py-2 text-start"
              :disabled="!issue.field_id"
              @click="goTo(issue.field_id)"
            >
              <span class="min-w-0">
                <span class="block text-sm text-highlighted">{{ t(`builder.issue.${issue.code}`) }}</span>
                <span v-if="labelOf(issue.field_id)" class="block truncate text-xs text-muted">{{
                  labelOf(issue.field_id)
                }}</span>
              </span>
            </UButton>
          </li>
        </ul>
      </div>
      <UFormField
        v-else
        :label="t('builder.publish.summary')"
        :hint="t('onboarding.optional')"
        :description="t('builder.publish.summaryHint')"
      >
        <UTextarea
          v-model="summary"
          :rows="3"
          maxlength="500"
          autoresize
          class="w-full"
          :placeholder="t('builder.publish.summaryPlaceholder')"
        />
      </UFormField>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="outline"
          class="justify-center"
          :disabled="props.busy"
          @click="open = false"
        />
        <UButton
          :label="props.republish ? t('builder.publish.submitAgain') : t('builder.publish.submit')"
          icon="i-lucide-globe"
          color="neutral"
          class="justify-center"
          :loading="props.busy"
          :disabled="!!issues.length"
          @click="emit('publish', summary.trim() || null)"
        />
      </div>
    </template>
  </AppModal>
</template>
