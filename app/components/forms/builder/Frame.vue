<!--
  Shared frame for the builder, logic and versions pages (one form, one session):
  header = inline name · status + "Saved just now" · Build / Logic / Versions (design segmented
  control) · undo / redo · Preview · Publish; body = loading / error / conflict states + the page.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{ session: BuilderSession; mode: 'build' | 'logic' | 'versions' }>()
const { t } = useI18n()
const s = props.session
const { builder, form, autosave } = s

const nameDraft = ref('')
watch(form, value => (nameDraft.value = value?.name ?? ''), { immediate: true })
async function saveName() {
  if (!(await s.rename(nameDraft.value))) nameDraft.value = form.value?.name ?? ''
}

const modes = computed(() => [
  { value: 'build', label: t('builder.mode.build'), icon: 'i-lucide-layout-panel-top' },
  { value: 'logic', label: t('builder.mode.logic'), icon: 'i-lucide-git-branch' },
  { value: 'versions', label: t('builder.mode.versions'), icon: 'i-lucide-history' },
])
const go = (mode: string | number) => navigateTo(`/forms/${s.formId}/${mode === 'build' ? 'build' : mode}`)

const publishOpen = ref(false)
const previewOpen = ref(false)
// Both dialogs load on first use (lazy components), then stay mounted for their close animation.
const publishUsed = ref(false)
const previewUsed = ref(false)
watch(publishOpen, v => v && (publishUsed.value = true))
watch(previewOpen, v => v && (previewUsed.value = true))
async function publish(summary: string | null) {
  if (await s.publish(summary)) publishOpen.value = false
}

const phoneMenu = computed<DropdownMenuItem[][]>(() => [
  modes.value.map(m => ({ label: m.label, icon: m.icon, type: 'checkbox' as const, checked: m.value === props.mode, onSelect: () => void go(m.value) })),
  [
    { label: t('builder.undo'), icon: 'i-lucide-undo-2', disabled: !builder.history.canUndo.value, onSelect: () => { builder.history.undo() } },
    { label: t('builder.redo'), icon: 'i-lucide-redo-2', disabled: !builder.history.canRedo.value, onSelect: () => { builder.history.redo() } },
  ],
  [{ label: t('builder.preview.button'), icon: 'i-lucide-eye', onSelect: () => { previewOpen.value = true } }],
])

const saveIcon = computed(() =>
  autosave.state.value === 'saving' || autosave.state.value === 'pending'
    ? 'i-lucide-loader-circle'
    : autosave.state.value === 'error' || autosave.state.value === 'conflict'
      ? 'i-lucide-cloud-alert'
      : 'i-lucide-refresh-cw',
)

defineShortcuts({
  meta_z: () => builder.history.undo(),
  meta_shift_z: () => builder.history.redo(),
  meta_y: () => builder.history.redo(),
})
</script>

<template>
  <AppPanel :id="`form-${mode}`" :title="form?.name ?? t('builder.crumb')">
    <template #title>
      <UInput
        v-if="form"
        v-model="nameDraft"
        variant="ghost"
        maxlength="120"
        :aria-label="t('forms.actions.rename')"
        :ui="{ base: 'px-1 -mx-1 text-base font-semibold text-highlighted sm:text-lg' }"
        class="min-w-0"
        @blur="saveName"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
        @keydown.esc="nameDraft = form.name"
      />
      <USkeleton v-else class="h-6 w-48" />
    </template>
    <template v-if="form" #meta>
      <span class="flex min-w-0 items-center gap-1.5" aria-live="polite">
        <DataStatusBadge :status="form.status" />
        <UBadge v-if="form.has_unpublished_changes" :label="t('builder.unpublished')" color="warning" variant="subtle" size="sm" class="rounded-md" />
        <UIcon :name="saveIcon" class="size-3 shrink-0" :class="autosave.state.value === 'saving' ? 'animate-spin' : ''" />
        <span class="truncate">{{ s.statusText.value }}</span>
      </span>
    </template>

    <template v-if="form" #actions>
      <UTabs
        :model-value="mode"
        :items="modes"
        :content="false"
        color="neutral"
        size="sm"
        :ui="{ ...SEGMENTED_UI, label: 'hidden xl:inline' }"
        class="hidden md:flex"
        :aria-label="t('builder.mode.label')"
        @update:model-value="go"
      />
      <UButton class="hidden sm:inline-flex" icon="i-lucide-undo-2" color="neutral" variant="outline" square :disabled="!builder.history.canUndo.value" :aria-label="t('builder.undo')" @click="builder.history.undo()" />
      <UButton class="hidden sm:inline-flex" icon="i-lucide-redo-2" color="neutral" variant="outline" square :disabled="!builder.history.canRedo.value" :aria-label="t('builder.redo')" @click="builder.history.redo()" />
      <UButton class="hidden sm:inline-flex" icon="i-lucide-eye" :label="t('builder.preview.button')" color="neutral" variant="outline" @click="previewOpen = true" />
      <!-- Phones / small tablets: modes, undo / redo and preview fold into one menu. -->
      <UDropdownMenu :items="phoneMenu" :content="{ align: 'end' }" class="md:hidden">
        <UButton class="md:hidden" icon="i-lucide-ellipsis" color="neutral" variant="outline" square :aria-label="t('builder.actions.more')" />
      </UDropdownMenu>
      <UButton icon="i-lucide-globe" :label="t('builder.publish.button')" color="neutral" :loading="s.publishing.value" @click="publishOpen = true" />
    </template>

    <slot v-if="s.loading.value" name="loading">
      <USkeleton class="mx-auto h-[60vh] w-full max-w-4xl" />
    </slot>

    <UEmpty
      v-else-if="s.failed.value"
      icon="i-lucide-file-question"
      :title="s.failed.value === 'FRM-GEN-1004' ? t('forms.detail.notFound') : t('dataView.errorTitle')"
      :actions="[
        { label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: s.load },
        { label: t('nav.forms'), to: '/forms', color: 'neutral' },
      ]"
      variant="outline"
    />

    <template v-else>
      <UAlert
        v-if="autosave.state.value === 'conflict'"
        icon="i-lucide-users"
        color="warning"
        variant="subtle"
        :title="t('builder.save.conflictTitle')"
        :description="t('builder.save.conflictDesc')"
        :actions="[{ label: t('builder.save.reload'), color: 'neutral', icon: 'i-lucide-rotate-cw', onClick: s.load }]"
      />
      <slot />
    </template>

    <LazyFormsBuilderPublishModal v-if="publishUsed" v-model:open="publishOpen" :busy="s.publishing.value" :republish="form?.status === 'published'" @publish="publish" />
    <LazyFormsBuilderPreviewModal v-if="previewUsed" v-model:open="previewOpen" />
  </AppPanel>
</template>
