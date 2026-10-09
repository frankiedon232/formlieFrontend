<!--
  The frame of every Settings page (F14). On desktop the Settings navigator takes over the menu column
  (useSidebarTakeover, the rail stays, an arrow goes back to the menu); on smaller screens a Sections
  button opens it in a side panel. The header holds the title, the section's line, who changed it last
  (or "Unsaved changes") and, for a form, Discard (outline) and Save (solid, Ctrl / ⌘ + S).
-->
<script setup lang="ts">
import type { SettingsChange } from '#shared/types/settings'

// `plain`: the same page in another area (People → Departments, Job titles; F16) without the Settings navigator
const props = defineProps<{ id: string; title: string; subtitle?: string; icon?: string; plain?: boolean; form?: { dirty: boolean; saving: boolean; updated: SettingsChange | null } }>()
const emit = defineEmits<{ save: []; discard: [] }>()
const { t } = useI18n()
const { relative } = useFormat()
const takeover = useSidebarTakeover()
if (!props.plain) takeover.claim(() => t('settings.title'), 'i-lucide-settings')
const sectionsOpen = ref(false)
watch(takeover.shown, shown => shown && (sectionsOpen.value = false))
</script>

<template>
  <AppPanel :id="id" :title="title" :subtitle="subtitle" :subtitle-icon="icon">
    <template v-if="form && (form.dirty || form.updated)" #meta>
      <span v-if="form.dirty" class="inline-flex items-center gap-1.5 text-xs font-medium text-warning"><span class="size-1.5 rounded-full bg-warning" />{{ t('settings.unsaved') }}</span>
      <span v-else-if="form.updated" class="truncate text-xs text-muted">{{ t('settings.changedBy', { when: relative(form.updated.at), name: form.updated.by }) }}</span>
    </template>
    <template #actions>
      <UButton v-if="!plain && !takeover.shown.value" :label="t('settings.sections')" icon="i-lucide-panel-left" color="neutral" variant="outline" class="lg:hidden" @click="sectionsOpen = true" />
      <UButton v-if="!plain && !takeover.shown.value" icon="i-lucide-panel-left" color="neutral" variant="outline" square class="hidden lg:inline-flex" :aria-label="t('settings.sections')" @click="sectionsOpen = true" />
      <slot name="actions" />
      <template v-if="props.form">
        <UButton :label="t('settings.discard')" color="neutral" variant="outline" :disabled="!props.form.dirty || props.form.saving" class="max-sm:hidden" @click="emit('discard')" />
        <UButton :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="props.form.saving" :disabled="!props.form.dirty" @click="emit('save')">
          <template #trailing><UKbd value="meta" size="sm" class="hidden xl:inline-flex" /><UKbd value="s" size="sm" class="hidden xl:inline-flex" /></template>
        </UButton>
      </template>
    </template>

    <slot />

    <Teleport v-if="takeover.shown.value" :to="`#${SIDEBAR_TAKEOVER_ID}`" defer>
      <SettingsNav />
    </Teleport>
    <USlideover v-model:open="sectionsOpen" side="left" :title="t('settings.title')" :ui="{ content: 'max-w-xs', body: 'p-0 sm:p-0 flex' }">
      <template #body>
        <SettingsNav @navigate="sectionsOpen = false" />
      </template>
    </USlideover>
  </AppPanel>
</template>
