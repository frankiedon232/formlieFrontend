<!--
  Form settings → Help guide (F10, owner 2026-10-03): turn the "?" button on or off (off by
  default) and open the editor. The guide itself lives in a window, not in this panel.
-->
<script setup lang="ts">
const { t } = useI18n()
const builder = useBuilder()
const schema = builder.schema

const guide = computed(() => schema.value?.settings?.guide ?? null)
const words = computed(() => {
  const text = (guide.value?.html ?? '').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').trim()
  return text ? text.split(/\s+/).length : 0
})
const editOpen = ref(false)
const editUsed = ref(false)
watch(editOpen, value => value && (editUsed.value = true))

function setEnabled(enabled: boolean) {
  if (!schema.value) return
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, guide: { title: guide.value?.title ?? '', html: guide.value?.html ?? '', enabled } }
  // Turning it on without a guide yet: open the editor straight away.
  if (enabled && !words.value) editOpen.value = true
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.guide.title') }}</h3>
    <USwitch
      :model-value="!!guide?.enabled"
      :label="t('builder.guide.enable')"
      :description="t('builder.guide.enableHint')"
      color="neutral"
      @update:model-value="setEnabled"
    />
    <div class="flex items-center justify-between gap-2 rounded-md border border-default px-3 py-2">
      <span class="flex min-w-0 items-center gap-2 text-sm">
        <UIcon :name="words ? 'i-lucide-book-open-check' : 'i-lucide-book-dashed'" class="size-4 shrink-0 text-muted" />
        <span class="truncate text-default">{{ words ? t('builder.guide.summary', { title: guide?.title || t('builder.guide.untitled'), n: words }, words) : t('builder.guide.empty') }}</span>
      </span>
      <UButton :label="words ? t('builder.guide.edit') : t('builder.guide.write')" :icon="words ? 'i-lucide-pencil' : 'i-lucide-plus'" color="neutral" variant="outline" size="xs" @click="editOpen = true" />
    </div>
    <p v-if="guide?.enabled && !words" class="text-xs text-warning">{{ t('builder.guide.noContent') }}</p>
    <LazyFormsBuilderGuideModal v-if="editUsed" v-model:open="editOpen" />
  </section>
</template>
