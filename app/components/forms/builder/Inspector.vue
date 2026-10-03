<!--
  Inspector (FRONTEND-SPEC §6, right pane) — a side card like the design's detail panel:
  nothing selected → form settings; one field → its settings; several → bulk width / required /
  move / duplicate / delete.
-->
<script setup lang="ts">
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { FIELD_WIDTHS } from '#shared/utils/forms/fields'

const { t } = useI18n()
const builder = useBuilder()
const { schema, selectedFields, selected, pages } = builder

const single = computed(() => (selectedFields.value.length === 1 ? selectedFields.value[0]! : null))
const widths = computed(() =>
  FIELD_WIDTHS.map(width => ({ value: String(width), label: t(`builder.widthShort.${width}`) })),
)
const saveOpen = ref(false)
const allRequired = computed(() => selectedFields.value.every(f => f.required))

function setRequiredAll(value: boolean) {
  builder.history.record()
  for (const field of selectedFields.value) field.required = value
}
const labelItems = computed(() => [
  { value: 'top', label: t('builder.labels.top') },
  { value: 'left', label: t('builder.labels.left') },
])
function setLabelPosition(value: string | number) {
  if (!schema.value) return
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, label_position: value === 'left' ? 'left' : 'top' }
}
/** The form's main language (decision 73): respondents get it unless the form offers theirs too. */
const languageItems = computed(() =>
  APP_LOCALES.map(item => ({ value: item.code, label: item.name, description: item.englishName, icon: item.flag })),
)
const languageFlag = computed(() => APP_LOCALES.find(item => item.code === (schema.value?.settings?.language ?? 'en'))?.flag)
function setLanguage(value: string) {
  if (!schema.value) return
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, language: value }
}
function setSetting(key: 'progress_bar' | 'save_resume', value: boolean) {
  if (!schema.value) return
  builder.history.record()
  schema.value.settings = { ...schema.value.settings, [key]: value }
}
function setThankYou(key: 'title' | 'message', value: string) {
  if (!schema.value) return
  builder.history.record(`thank_you:${key}`)
  schema.value.thank_you = { ...schema.value.thank_you, [key]: value }
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="mb-4 flex items-center gap-2.5">
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50"
      >
        <UIcon
          :name="
            single ? fieldIcon(single.type) : selected.length > 1 ? 'i-lucide-layers' : 'i-lucide-settings-2'
          "
          class="size-4 text-highlighted"
        />
      </span>
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-highlighted">
          {{
            single
              ? t(`builder.field.${single.type}`)
              : selected.length > 1
                ? t('builder.inspector.selected', { count: selected.length }, selected.length)
                : t('builder.inspector.formSettings')
          }}
        </p>
        <p class="truncate text-xs text-muted">
          {{
            single
              ? single.key
              : selected.length > 1
                ? t('builder.inspector.bulkHint')
                : t('builder.inspector.selectHint')
          }}
        </p>
      </div>
      <UTooltip v-if="single" :text="t('library.saveFieldHint')">
        <UButton
          icon="i-lucide-bookmark-plus"
          :label="t('library.saveShort')"
          color="neutral"
          variant="outline"
          size="xs"
          class="ms-auto shrink-0"
          @click="saveOpen = true"
        />
      </UTooltip>
      <FormsBuilderSaveFieldModal v-if="single" v-model:open="saveOpen" :field="single" />
    </div>

    <div class="-me-2 min-h-0 flex-1 overflow-y-auto pe-2">
      <FormsBuilderInspectorField v-if="single" :key="single.id" :field="single" />

      <div v-else-if="selected.length > 1" class="flex flex-col gap-4">
        <UFormField :label="t('builder.inspector.width')">
          <UTabs
            :model-value="''"
            :items="widths"
            :content="false"
            color="neutral"
            size="xs"
            :ui="SEGMENTED_UI"
            class="w-full"
            @update:model-value="v => builder.setWidth(selected, Number(v))"
          />
        </UFormField>
        <USwitch
          :model-value="allRequired"
          :label="t('builder.inspector.required')"
          color="neutral"
          @update:model-value="setRequiredAll"
        />
        <USelect
          v-if="pages.length > 1"
          :model-value="undefined"
          :items="
            pages.map((p, i) => ({ value: p.id, label: p.title || t('builder.page.default', { n: i + 1 }) }))
          "
          value-key="value"
          :placeholder="t('builder.actions.moveToPage')"
          class="w-full"
          @update:model-value="v => builder.moveToPage(selected, String(v))"
        />
        <div class="flex gap-2">
          <UButton
            :label="t('builder.actions.duplicate')"
            icon="i-lucide-copy"
            color="neutral"
            variant="outline"
            size="sm"
            @click="builder.duplicate()"
          />
          <UButton
            :label="t('builder.actions.delete')"
            icon="i-lucide-trash-2"
            color="error"
            variant="outline"
            size="sm"
            @click="builder.removeWithUndo()"
          />
        </div>
      </div>

      <div v-else-if="schema" class="flex flex-col gap-6">
        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.labels.title') }}</h3>
          <UFormField :description="t('builder.labels.hint')">
            <UTabs
              :model-value="schema.settings?.label_position ?? 'top'"
              :items="labelItems"
              :content="false"
              color="neutral"
              size="xs"
              :ui="{ ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1 px-1.5` }"
              class="w-full"
              :aria-label="t('builder.labels.title')"
              @update:model-value="setLabelPosition"
            />
          </UFormField>
        </section>
        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.language.title') }}</h3>
          <UFormField :description="t('builder.language.hint')">
            <USelectMenu
              :model-value="schema.settings?.language ?? 'en'"
              :items="languageItems"
              value-key="value"
              :search-input="{ placeholder: t('common.search') }"
              :icon="languageFlag"
              class="w-full"
              :aria-label="t('builder.language.title')"
              @update:model-value="v => setLanguage(String(v))"
            />
          </UFormField>
        </section>
        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.experience') }}</h3>
          <USwitch
            :model-value="schema.settings?.progress_bar !== false"
            :label="t('builder.inspector.progressBar')"
            :description="t('builder.inspector.progressBarHint')"
            color="neutral"
            @update:model-value="v => setSetting('progress_bar', v)"
          />
          <USwitch
            :model-value="!!schema.settings?.save_resume"
            :label="t('builder.inspector.saveResume')"
            :description="t('builder.inspector.saveResumeHint')"
            color="neutral"
            @update:model-value="v => setSetting('save_resume', v)"
          />
        </section>
        <FormsBuilderIdentitySetting />
        <FormsBuilderGuideSetting />
        <FormsBuilderTemplateSetting />
        <section class="flex flex-col gap-3">
          <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.inspector.thankYou') }}</h3>
          <UFormField :label="t('builder.inspector.title')">
            <UInput
              :model-value="schema.thank_you?.title ?? ''"
              class="w-full"
              @update:model-value="v => setThankYou('title', String(v))"
            />
          </UFormField>
          <UFormField :label="t('builder.inspector.message')">
            <UTextarea
              :model-value="schema.thank_you?.message ?? ''"
              :rows="3"
              autoresize
              class="w-full"
              @update:model-value="v => setThankYou('message', String(v))"
            />
          </UFormField>
        </section>
        <section
          class="flex flex-col gap-2 rounded-lg border border-dashed border-default p-3 text-xs text-muted"
        >
          <p class="font-medium text-default">{{ t('builder.shortcuts.title') }}</p>
          <p class="flex items-center gap-1.5">
            <UKbd value="meta" /><UKbd value="z" /> {{ t('builder.shortcuts.undo') }}
          </p>
          <p class="flex items-center gap-1.5">
            <UKbd value="meta" /><UKbd value="d" /> {{ t('builder.shortcuts.duplicate') }}
          </p>
          <p class="flex items-center gap-1.5">
            <UKbd value="alt" /><UKbd value="arrowup" /><UKbd value="arrowdown" />
            {{ t('builder.shortcuts.move') }}
          </p>
          <p class="flex items-center gap-1.5"><UKbd value="delete" /> {{ t('builder.shortcuts.delete') }}</p>
        </section>
      </div>
    </div>
  </div>
</template>
