<!--
  Form settings → Template (owner, 2026-10-03), after "Save and resume". A form that isn't a template
  yet can be saved as one. Once it is, this says so and "Update template" puts the form's latest
  changes into that same template — no second template. Saving a separate copy stays possible,
  clearly marked as a new template. Pending edits are saved first so the template matches the screen.
-->
<script setup lang="ts">
import type { TemplateSummary } from '#shared/types/templates'

const { t } = useI18n()
const session = injectBuilderSession()
const templates = useTemplates()
const { relative } = useFormat()

const linked = ref<TemplateSummary | null>(null)
const loading = ref(true)
async function load() {
  if (!session) return
  loading.value = true
  try {
    linked.value = await templates.fromForm(session.formId)
  } catch {
    linked.value = null // Not knowing just means we offer "Save as template".
  } finally {
    loading.value = false
  }
}
onMounted(load)

const form = computed(() => session?.form.value ?? null)
const saveOpen = ref(false)
const saveUsed = ref(false)
watch(saveOpen, value => {
  if (value) saveUsed.value = true
  else void load() // A new template may have been saved.
})

const { busy: preparing, run: prepare } = useBusy()
async function saveNew() {
  await prepare(async () => {
    await session?.autosave.saveNow()
    saveOpen.value = true
  })
}
const { busy: updating, run: runUpdate } = useBusy()
async function update() {
  if (!linked.value) return
  await runUpdate(async () => {
    await session?.autosave.saveNow()
    const saved = await templates.syncFromForm(linked.value!)
    if (saved) linked.value = { ...linked.value!, updated_at: saved.updated_at }
  })
}
</script>

<template>
  <section v-if="session" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.template.title') }}</h3>

    <USkeleton v-if="loading" class="h-16 w-full" />

    <template v-else-if="linked">
      <UAlert
        icon="i-lucide-bookmark-check"
        color="neutral"
        variant="subtle"
        :title="t('builder.template.savedAs', { name: linked.name })"
        :description="t('builder.template.savedAsHint', { when: relative(linked.updated_at) })"
        :ui="{ description: 'text-xs' }"
      />
      <div class="flex flex-wrap gap-2">
        <UButton :label="t('builder.template.update')" icon="i-lucide-refresh-cw" color="neutral" size="sm" :loading="updating" :disabled="preparing" @click="update" />
        <UButton :label="t('templates.view')" icon="i-lucide-eye" color="neutral" variant="ghost" size="sm" :to="`/templates/${linked.key}`" />
      </div>
      <UButton
        :label="t('builder.template.saveNew')"
        icon="i-lucide-copy-plus"
        color="neutral"
        variant="link"
        size="xs"
        class="self-start px-0"
        :loading="preparing"
        :disabled="updating"
        @click="saveNew"
      />
      <p class="-mt-2 text-xs text-muted">{{ t('builder.template.saveNewHint') }}</p>
    </template>

    <template v-else>
      <p class="text-xs text-muted">{{ t('builder.template.hint') }}</p>
      <UButton :label="t('templates.saveAs')" icon="i-lucide-bookmark-plus" color="neutral" variant="outline" size="sm" class="self-start" :loading="preparing" @click="saveNew" />
    </template>

    <LazyTemplatesSaveModal v-if="saveUsed && form" v-model:open="saveOpen" :form="form" />
  </section>
</template>
