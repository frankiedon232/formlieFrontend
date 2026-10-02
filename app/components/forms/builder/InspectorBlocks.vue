<!--
  Settings for layout blocks: section style (size, divider, alignment), paragraph (edited on the
  canvas — hint only), divider style and spacing, image (alt text, caption, width, alignment,
  link on click, rounded corners, image link / upload hint).
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()

const has = (control: InspectorControl) => hasControl(props.field.type, control)
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const setProp = (patch: Record<string, unknown>, group?: string) => builder.updateProps(props.field.id, patch, group)
const text = (key: string) => (typeof p.value[key] === 'string' ? (p.value[key] as string) : '')
const tabsUi = { ...SEGMENTED_UI, trigger: `${SEGMENTED_UI.trigger} flex-1 px-1.5` }

const sizes = computed(() => [
  { value: 'lg', label: t('builder.blocks.sizeLarge') },
  { value: 'md', label: t('builder.blocks.sizeMedium') },
  { value: 'sm', label: t('builder.blocks.sizeSmall') },
])
const sectionAlign = computed(() => [
  { value: 'start', label: t('builder.blocks.alignStart'), icon: 'i-lucide-align-left' },
  { value: 'center', label: t('builder.blocks.alignCenter'), icon: 'i-lucide-align-center' },
])
const imageAlign = computed(() => [
  { value: 'start', label: t('builder.blocks.alignStart') },
  { value: 'center', label: t('builder.blocks.alignCenter') },
  { value: 'end', label: t('builder.blocks.alignEnd') },
  { value: 'fill', label: t('builder.blocks.fill') },
])
const fill = computed(() => p.value.align === 'fill')
const imageHeights = computed(() => [
  { value: 'auto', label: t('builder.blocks.heightAuto') },
  { value: 'sm', label: t('builder.blocks.sizeSmall') },
  { value: 'md', label: t('builder.blocks.sizeMedium') },
  { value: 'lg', label: t('builder.blocks.sizeLarge') },
])
const imageSizes = [25, 50, 75, 100].map(n => ({ value: String(n), label: `${n}%` }))
const dividerStyles = computed(() => [
  { value: 'solid', label: t('builder.blocks.solid') },
  { value: 'dashed', label: t('builder.blocks.dashed') },
  { value: 'dotted', label: t('builder.blocks.dotted') },
])
const spacings = computed(() => [
  { value: 'sm', label: t('builder.blocks.sizeSmall') },
  { value: 'md', label: t('builder.blocks.sizeMedium') },
  { value: 'lg', label: t('builder.blocks.sizeLarge') },
])

const hrefError = computed(() => (text('href') && !/^https?:\/\/\S+$/i.test(text('href')) ? t('builder.blocks.linkInvalid') : ''))
const srcError = computed(() => (text('src') && !text('upload_id') && !/^https:\/\/\S+$/i.test(text('src')) ? t('builder.blocks.linkInvalid') : ''))
</script>

<template>
  <section
    v-if="has('section_style') || has('paragraph') || has('divider_style') || has('image')"
    class="flex flex-col gap-3"
  >
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.blocks.appearance') }}</h3>

    <!-- Section -->
    <template v-if="has('section_style')">
      <UFormField :label="t('builder.blocks.size')">
        <UTabs :model-value="text('size') || 'lg'" :items="sizes" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ size: v })" />
      </UFormField>
      <UFormField :label="t('builder.blocks.align')">
        <UTabs :model-value="text('align') || 'start'" :items="sectionAlign" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ align: v })" />
      </UFormField>
      <USwitch :model-value="p.divider !== false" :label="t('builder.blocks.dividerLine')" color="neutral" @update:model-value="v => setProp({ divider: v })" />
    </template>

    <!-- Paragraph -->
    <UAlert
      v-if="has('paragraph')"
      icon="i-lucide-mouse-pointer-click"
      color="neutral"
      variant="subtle"
      :description="t('builder.blocks.paragraphHint')"
    />

    <!-- Divider -->
    <template v-if="has('divider_style')">
      <UFormField :label="t('builder.blocks.lineStyle')">
        <UTabs :model-value="text('style') || 'solid'" :items="dividerStyles" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ style: v })" />
      </UFormField>
      <UFormField :label="t('builder.blocks.spacing')">
        <UTabs :model-value="text('spacing') || 'md'" :items="spacings" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ spacing: v })" />
      </UFormField>
    </template>

    <!-- Image -->
    <template v-if="has('image')">
      <p v-if="!text('src')" class="text-xs text-muted">{{ t('builder.blocks.imageOnCanvas') }}</p>
      <UFormField v-if="!text('upload_id')" :label="t('builder.inspector.imageUrl')" :error="srcError || undefined">
        <UInput type="url" :model-value="text('src')" placeholder="https://" class="w-full" @update:model-value="v => setProp({ src: String(v) }, `image:${field.id}:src`)" />
      </UFormField>
      <UFormField
        :label="t('builder.inspector.alt')"
        :description="t('builder.inspector.altHint')"
        :error="text('src') && !text('alt') ? t('builder.blocks.altMissing') : undefined"
      >
        <UInput :model-value="text('alt')" class="w-full" @update:model-value="v => setProp({ alt: String(v) }, `image:${field.id}:alt`)" />
      </UFormField>
      <UFormField :label="t('builder.blocks.caption')">
        <UInput :model-value="text('caption')" class="w-full" @update:model-value="v => setProp({ caption: String(v) }, `image:${field.id}:caption`)" />
      </UFormField>
      <UFormField v-if="!fill" :label="t('builder.blocks.imageWidth')" :hint="`${Number(p.size ?? 100)}%`">
        <UTabs
          :model-value="String(p.size ?? 100)"
          :items="imageSizes"
          :content="false"
          color="neutral"
          size="xs"
          :ui="tabsUi"
          class="w-full"
          @update:model-value="v => setProp({ size: Number(v) })"
        />
      </UFormField>
      <UFormField :label="t('builder.blocks.align')">
        <UTabs :model-value="text('align') || 'center'" :items="imageAlign" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ align: v })" />
      </UFormField>
      <UFormField v-if="fill" :label="t('builder.blocks.height')" :description="t('builder.blocks.heightHint')">
        <UTabs :model-value="text('height') || 'auto'" :items="imageHeights" :content="false" color="neutral" size="xs" :ui="tabsUi" class="w-full" @update:model-value="v => setProp({ height: v })" />
      </UFormField>
      <UFormField :label="t('builder.blocks.href')" :description="t('builder.blocks.hrefHint')" :error="hrefError || undefined">
        <UInput type="url" :model-value="text('href')" placeholder="https://" icon="i-lucide-external-link" class="w-full" @update:model-value="v => setProp({ href: String(v) }, `image:${field.id}:href`)" />
      </UFormField>
      <USwitch :model-value="p.rounded !== false" :label="t('builder.blocks.rounded')" color="neutral" @update:model-value="v => setProp({ rounded: v })" />
    </template>
  </section>
</template>
