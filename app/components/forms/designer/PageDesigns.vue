<!--
  Designer → Page designs (owner 2026-10-04: "in design you can add it", listed like the themes):
  every page design, the workspace's own first, then Formalie's, as page miniatures. A click puts
  that page around the form (only the page changes, one undo step, no confirm: the toast offers Undo). "Save page as design" keeps this form's page in Resources → Landing pages.
-->
<script setup lang="ts">
import type { PageDesign } from '#shared/types/forms'

const { t } = useI18n()
const d = useDesigner()
const library = usePageDesigns()
onMounted(() => library.load())

const ordered = computed(() => [...library.pages.value].sort((a, b) => Number(a.source === 'system') - Number(b.source === 'system')))
const current = computed(() => library.pages.value.find(page => page.id === d.pageDesignId.value) ?? null)
// Save as a new landing page (pages.create) or update the one the form uses when this person may change it (F22 R2 M3)
const canCreate = computed(() => useCan().can('pages.create'))
const updatable = computed(() => (current.value?.can?.edit ? current.value : null))
const saveOpen = ref(false)

function apply(page: PageDesign) {
  if (page.id === d.pageDesignId.value) return
  d.applyPage(page)
  d.applied(page.name_key ? t(page.name_key) : page.name)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <p class="text-xs text-muted">{{ t('pages.designerHint') }}</p>
      <UButton v-if="canCreate || updatable" :label="t('pages.saveShort')" icon="i-lucide-bookmark-plus" color="neutral" variant="outline" size="xs" class="shrink-0" @click="saveOpen = true" />
    </div>
    <div v-if="library.loading.value && !library.loaded.value" class="grid grid-cols-2 gap-2" :aria-label="t('common.loading')">
      <USkeleton v-for="i in 4" :key="i" class="aspect-video" />
    </div>
    <div v-else class="grid max-h-80 grid-cols-2 gap-2 overflow-y-auto pe-0.5">
      <button
        v-for="page in ordered"
        :key="page.id"
        type="button"
        class="flex flex-col gap-1.5 rounded-lg border p-1.5 text-start transition-colors hover:border-accented focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="page.id === d.pageDesignId.value ? 'border-inverted ring-1 ring-inverted' : 'border-default'"
        :aria-pressed="page.id === d.pageDesignId.value"
        :aria-label="t('pages.apply', { name: library.nameOf(page) })"
        @click="apply(page)"
      >
        <span class="block overflow-hidden rounded-md border border-default"><PageDesignsThumb :tokens="page.tokens" /></span>
        <span class="flex min-w-0 items-center gap-1 px-0.5">
          <UIcon v-if="page.source !== 'system'" name="i-lucide-bookmark" class="size-3 shrink-0 text-muted" />
          <span class="truncate text-xs font-medium text-highlighted">{{ library.nameOf(page) }}</span>
        </span>
      </button>
    </div>
    <UButton :label="t('pages.manage')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="link" size="xs" to="/settings/landing-pages" target="_blank" class="self-start px-0 rtl:[&_.iconify]:-scale-x-100" />
    <FormsDesignerSavePageModal v-model:open="saveOpen" :current="updatable" :can-create="canCreate" />
  </div>
</template>
