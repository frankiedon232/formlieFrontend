<!--
  Designer (FRONTEND-SPEC §7, PROGRESS F8): design controls on the left, the live form page on
  the right — desktop / tablet / phone and questions / thank-you page. Below laptop width the
  preview fills the screen and the controls open from a floating "Design" bar (slide-over on
  tablets, drawer on phones). Same header, autosave and undo as the builder.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'designer.crumb' })

const { t } = useI18n()
const route = useRoute()
const session = useBuilderSession(String(route.params.id))
const { builder, form } = session
useHead({ title: () => (form.value ? `${form.value.name} · ${t('designer.crumb')}` : t('designer.crumb')) })

const large = useMediaQuery('(min-width: 1024px)')
const tablet = useMediaQuery('(min-width: 768px)')
const panelOpen = ref(false)

const device = ref<'desktop' | 'tablet' | 'phone'>('desktop')
const devices = computed(() => [
  { value: 'desktop', label: t('builder.preview.desktop'), icon: 'i-lucide-monitor' },
  { value: 'tablet', label: t('builder.preview.tablet'), icon: 'i-lucide-tablet' },
  { value: 'phone', label: t('builder.preview.phone'), icon: 'i-lucide-smartphone' },
])
const WIDTH = { desktop: 'max-w-full', tablet: 'max-w-[768px]', phone: 'max-w-[390px]' }
const screen = ref<'form' | 'thanks'>('form')
const screens = computed(() => [
  { value: 'form', label: t('designer.screen.form') },
  { value: 'thanks', label: t('designer.screen.thanks') },
])
const paneHeight = computed(() => (session.fullscreen.value ? 'h-[calc(100dvh-5.5rem)]' : 'h-[calc(100dvh-11rem)]'))
</script>

<template>
  <FormsBuilderFrame :session="session" mode="design">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]" :aria-label="t('common.loading')">
        <USkeleton class="hidden h-[70vh] lg:block" />
        <USkeleton class="h-[70vh] w-full" />
      </div>
    </template>

    <div class="grid items-start gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
      <UCard v-if="large" class="sticky top-0" :ui="{ body: `p-4 sm:p-4 overflow-y-auto ${paneHeight}` }">
        <FormsDesignerPanel />
      </UCard>

      <!-- The preview fills the pane like a real page (owner, 2026-10-03): the form's background reaches the bottom, the page scrolls inside. -->
      <div class="mb-20 flex min-w-0 flex-col gap-3 rounded-xl bg-elevated/40 p-2 sm:p-3 lg:mb-0" :class="large ? paneHeight : 'min-h-[70dvh]'">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <UTabs v-model="screen" :items="screens" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('designer.screen.label')" />
          <UTabs
            v-model="device"
            :items="devices"
            :content="false"
            color="neutral"
            size="xs"
            :ui="{ ...SEGMENTED_UI, label: 'hidden md:inline' }"
            class="hidden sm:flex"
            :aria-label="t('builder.preview.device')"
          />
        </div>
        <div
          class="mx-auto flex min-h-0 w-full flex-1 flex-col overflow-y-auto rounded-lg border border-default transition-[max-width] duration-300 @container"
          :class="WIDTH[device]"
        >
          <FormsRendererPage
            v-if="builder.schema.value"
            :schema="builder.schema.value"
            :title="form?.name ?? ''"
            :show-thank-you="screen === 'thanks'"
            preview
            framed
          />
        </div>
      </div>
    </div>

    <template v-if="!large">
      <div class="pointer-events-none sticky bottom-3 z-20 mt-3 flex justify-center">
        <div class="pointer-events-auto rounded-xl border border-default bg-default p-1 shadow-lg">
          <UButton icon="i-lucide-palette" :label="t('builder.mode.design')" color="neutral" @click="panelOpen = true" />
        </div>
      </div>
      <USlideover v-if="tablet" v-model:open="panelOpen" side="left" :title="t('builder.mode.design')">
        <template #body><FormsDesignerPanel /></template>
      </USlideover>
      <UDrawer v-else v-model:open="panelOpen" :title="t('builder.mode.design')" :ui="{ body: 'max-h-[75dvh] overflow-y-auto' }">
        <template #body><FormsDesignerPanel /></template>
      </UDrawer>
    </template>
  </FormsBuilderFrame>
</template>
