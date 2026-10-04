<!--
  The form editor's Share tab (F10 M3): who can open the form, its custom link, limits and
  availability, with the live link, QR code and embed code alongside (FormsShareSettings).
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'share.crumb' })

const { t } = useI18n()
const route = useRoute()
const session = useBuilderSession(String(route.params.id))
const { form } = session
useHead({ title: () => (form.value ? `${form.value.name} · ${t('share.crumb')}` : t('share.crumb')) })
</script>

<template>
  <FormsBuilderFrame :session="session" mode="share">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]" :aria-label="t('common.loading')">
        <div class="flex flex-col gap-4">
          <USkeleton v-for="i in 3" :key="i" class="h-48 w-full rounded-lg" />
        </div>
        <USkeleton class="h-72 w-full rounded-lg" />
      </div>
    </template>

    <FormsShareSettings :session="session" />
  </FormsBuilderFrame>
</template>
