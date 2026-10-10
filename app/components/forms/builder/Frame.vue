<!--
  Shared frame for the builder, logic and versions pages (one form, one session):
  header = inline name · status + "Saved just now" · Build / Logic / Design / Share / Versions (design segmented
  control) · undo / redo · Preview · Publish; body = loading / error / conflict states + the page.
  Each part follows what this person may do with the form (F22 R2): Build / Logic / Design need edit, Share
  needs to see share settings, Versions needs versions; renaming, publishing and preview are their own.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const props = defineProps<{ session: BuilderSession; mode: 'build' | 'logic' | 'design' | 'share' | 'versions' }>()
const { t } = useI18n()
const s = props.session
const { builder, form, autosave } = s
provideBuilderSession(s)

const nameDraft = ref('')
watch(form, value => (nameDraft.value = value?.name ?? ''), { immediate: true })
async function saveName() {
  if (!(await s.rename(nameDraft.value))) nameDraft.value = form.value?.name ?? ''
}

const allowed = (action: Parameters<typeof formCan>[1]) => formCan(form.value, action)
const NEEDS = { build: 'edit', logic: 'edit', design: 'edit', share: 'share_view', versions: 'versions' } as const
/** May they be on this tab at all? (Otherwise the page explains and offers the way back.) */
const canHere = computed(() => allowed(NEEDS[props.mode]))
const modes = computed(() =>
  [
    { value: 'build', label: t('builder.mode.build'), icon: 'i-lucide-layout-panel-top' },
    { value: 'logic', label: t('builder.mode.logic'), icon: 'i-lucide-git-branch' },
    { value: 'design', label: t('builder.mode.design'), icon: 'i-lucide-palette' },
    { value: 'share', label: t('builder.mode.share'), icon: 'i-lucide-share-2' },
    { value: 'versions', label: t('builder.mode.versions'), icon: 'i-lucide-history' },
  ].filter(item => allowed(NEEDS[item.value as keyof typeof NEEDS])),
)
const go = (mode: string | number) => navigateTo(`/forms/${s.formId}/${mode === 'build' ? 'build' : mode}`)

const publishOpen = ref(false)
const previewOpen = ref(false)
// The AI assistant's help (F19 M3): on Build and Logic, for people who may edit the form and use builder help
const { can } = useCan()
const canAssist = computed(() => (props.mode === 'build' || props.mode === 'logic') && s.canEdit.value && can('ai.assist'))
const assistOpen = ref(false)
const assistUsed = ref(false)
watch(assistOpen, v => v && (assistUsed.value = true))
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
  s.canEdit.value
    ? [
        { label: t('builder.undo'), icon: 'i-lucide-undo-2', disabled: !builder.history.canUndo.value, onSelect: () => { builder.history.undo() } },
        { label: t('builder.redo'), icon: 'i-lucide-redo-2', disabled: !builder.history.canRedo.value, onSelect: () => { builder.history.redo() } },
      ]
    : [],
  allowed('preview') ? [{ label: t('builder.preview.button'), icon: 'i-lucide-eye', onSelect: () => { previewOpen.value = true } }] : [],
  canAssist.value ? [{ label: t('ai.assist.title'), icon: 'i-lucide-sparkles', onSelect: () => { assistOpen.value = true } }] : [],
].filter(group => group.length))

defineShortcuts({
  meta_z: () => builder.history.undo(),
  meta_shift_z: () => builder.history.redo(),
  meta_y: () => builder.history.redo(),
  meta_shift_f: () => s.toggleFullscreen(),
})
</script>

<template>
  <AppPanel :id="`form-${mode}`" :title="form?.name ?? t('builder.crumb')" compact-search>
    <template #title>
      <UInput
        v-if="form && allowed('rename')"
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
      <USkeleton v-else-if="s.loading.value" class="h-6 w-48" />
      <span v-else class="truncate text-base font-semibold text-highlighted sm:text-lg">{{ form?.name ?? t('builder.crumb') }}</span>
    </template>
    <template v-if="form && s.canEdit.value" #meta>
      <FormsBuilderSaveStatus :session="s" />
    </template>

    <template v-if="form && canHere" #actions>
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
      <UButton v-if="canAssist" class="hidden md:inline-flex" icon="i-lucide-sparkles" :label="t('ai.assist.button')" color="neutral" variant="outline" :ui="{ label: 'hidden xl:inline' }" :aria-label="t('ai.assist.title')" @click="assistOpen = true" />
      <UButton v-if="s.canEdit.value" class="hidden sm:inline-flex" icon="i-lucide-undo-2" color="neutral" variant="outline" square :disabled="!builder.history.canUndo.value" :aria-label="t('builder.undo')" @click="builder.history.undo()" />
      <UButton v-if="s.canEdit.value" class="hidden sm:inline-flex" icon="i-lucide-redo-2" color="neutral" variant="outline" square :disabled="!builder.history.canRedo.value" :aria-label="t('builder.redo')" @click="builder.history.redo()" />
      <UTooltip v-if="s.canEdit.value" :text="t('builder.fullscreen.enter')" :kbds="['meta', 'shift', 'f']">
        <UButton class="hidden lg:inline-flex" icon="i-lucide-maximize-2" color="neutral" variant="outline" square :aria-label="t('builder.fullscreen.enter')" @click="s.toggleFullscreen(true)" />
      </UTooltip>
      <UTooltip v-if="allowed('preview')" :text="t('builder.preview.button')">
        <UButton class="hidden sm:inline-flex" icon="i-lucide-eye" color="neutral" variant="outline" square :aria-label="t('builder.preview.button')" @click="previewOpen = true" />
      </UTooltip>
      <!-- Phones / small tablets: modes, undo / redo and preview fold into one menu. -->
      <UDropdownMenu :items="phoneMenu" :content="{ align: 'end' }" class="md:hidden">
        <UButton class="md:hidden" icon="i-lucide-ellipsis" color="neutral" variant="outline" square :aria-label="t('builder.actions.more')" />
      </UDropdownMenu>
      <!-- Nothing new since the last publish: not clickable, and it says why on hover (owner 2026-10-08) -->
      <UTooltip v-if="allowed('publish')" :text="t('builder.publish.nothing')" :disabled="!s.nothingToPublish.value">
        <span class="inline-flex" :tabindex="s.nothingToPublish.value ? 0 : undefined" :aria-label="s.nothingToPublish.value ? t('builder.publish.nothing') : undefined">
          <UButton icon="i-lucide-globe" :label="t('builder.publish.button')" color="neutral" :loading="s.publishing.value" :disabled="s.nothingToPublish.value" :class="s.nothingToPublish.value ? 'opacity-50!' : ''" @click="publishOpen = true" />
        </span>
      </UTooltip>
    </template>

    <slot v-if="s.loading.value" name="loading">
      <USkeleton class="mx-auto h-[60vh] w-full max-w-4xl" />
    </slot>

    <!-- "Can view" / "Responses only" (people access, decision 97): never the editor, only the way back. -->
    <AppEmpty
      v-else-if="s.failed.value === 'FRM-PERM-1001' || (form && !canHere)"
      icon="i-lucide-eye"
      :title="t('share.people.noEditor')"
      :description="t('share.people.noEditorDesc')"
      :actions="[
        { label: t('share.people.backToForm'), to: `/forms/${s.formId}`, color: 'neutral', icon: 'i-lucide-arrow-left' },
        { label: t('forms.viewResponses'), to: `/forms/${s.formId}/responses`, color: 'neutral', variant: 'outline', icon: 'i-lucide-inbox' },
      ]"
      variant="outline"
    />
    <AppEmpty
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
      <!-- Full screen: the same content moves into a layer over the app (state is kept), under a
           slim bar with the name, save status and the main actions. -->
      <Teleport to="body" :disabled="!s.fullscreen.value">
        <div
          :class="s.fullscreen.value ? 'fixed inset-0 z-40 flex flex-col bg-default' : 'contents'"
          :role="s.fullscreen.value ? 'region' : undefined"
          :aria-label="s.fullscreen.value ? t('builder.fullscreen.label') : undefined"
        >
          <div v-if="s.fullscreen.value" class="flex h-12 shrink-0 items-center gap-2 border-b border-default px-3 sm:px-4">
            <p class="min-w-0 truncate text-sm font-semibold text-highlighted">{{ form?.name }}</p>
            <FormsBuilderSaveStatus :session="s" class="min-w-0" />
            <div class="ms-auto flex shrink-0 items-center gap-1.5">
              <UTabs
                :model-value="mode"
                :items="modes"
                :content="false"
                color="neutral"
                size="xs"
                :ui="{ ...SEGMENTED_UI, label: 'hidden xl:inline' }"
                class="hidden md:flex"
                :aria-label="t('builder.mode.label')"
                @update:model-value="go"
              />
              <UButton v-if="canAssist" icon="i-lucide-sparkles" color="neutral" variant="ghost" size="sm" square :aria-label="t('ai.assist.title')" @click="assistOpen = true" />
              <UButton v-if="s.canEdit.value" icon="i-lucide-undo-2" color="neutral" variant="ghost" size="sm" square :disabled="!builder.history.canUndo.value" :aria-label="t('builder.undo')" @click="builder.history.undo()" />
              <UButton v-if="s.canEdit.value" icon="i-lucide-redo-2" color="neutral" variant="ghost" size="sm" square :disabled="!builder.history.canRedo.value" :aria-label="t('builder.redo')" @click="builder.history.redo()" />
              <UButton v-if="allowed('preview')" icon="i-lucide-eye" :label="t('builder.preview.button')" color="neutral" variant="outline" size="sm" class="hidden sm:inline-flex" @click="previewOpen = true" />
              <UTooltip v-if="allowed('publish')" :text="t('builder.publish.nothing')" :disabled="!s.nothingToPublish.value">
                <span class="inline-flex" :tabindex="s.nothingToPublish.value ? 0 : undefined" :aria-label="s.nothingToPublish.value ? t('builder.publish.nothing') : undefined">
                  <UButton icon="i-lucide-globe" :label="t('builder.publish.button')" color="neutral" size="sm" :loading="s.publishing.value" :disabled="s.nothingToPublish.value" :class="s.nothingToPublish.value ? 'opacity-50!' : ''" @click="publishOpen = true" />
                </span>
              </UTooltip>
              <UTooltip :text="t('builder.fullscreen.exit')" :kbds="['esc']">
                <UButton icon="i-lucide-minimize-2" color="neutral" variant="outline" size="sm" square :aria-label="t('builder.fullscreen.exit')" @click="s.toggleFullscreen(false)" />
              </UTooltip>
            </div>
          </div>
          <div :class="s.fullscreen.value ? 'min-h-0 flex-1 overflow-y-auto p-3 sm:p-4' : 'contents'">
            <slot />
          </div>
        </div>
      </Teleport>
    </template>

    <LazyFormsBuilderPublishModal v-if="publishUsed" v-model:open="publishOpen" :busy="s.publishing.value" :republish="form?.status === 'published'" :form-id="s.formId" @publish="publish" />
    <LazyFormsBuilderPreviewModal v-if="previewUsed" v-model:open="previewOpen" :form-name="form?.name" />
    <LazyAiBuilderAssistant v-if="assistUsed && canAssist" v-model:open="assistOpen" :form-id="s.formId" />
  </AppPanel>
</template>
