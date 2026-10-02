<!--
  Form logic (FRONTEND-SPEC §6, PROGRESS F7): rules as cards with a plain-language sentence
  ("When Severity is High, require Photos."), edited in place; calculated-field formulas beside
  them on large screens, below on phones. Same header, autosave and undo as the builder.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'logic.crumb' })

const { t } = useI18n()
const route = useRoute()
const session = useBuilderSession(String(route.params.id))
const { form } = session
useHead({ title: () => (form.value ? `${form.value.name} · ${t('logic.crumb')}` : t('logic.crumb')) })
</script>

<template>
  <FormsBuilderFrame :session="session" mode="logic">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]" :aria-label="t('common.loading')">
        <div class="flex flex-col gap-3">
          <USkeleton v-for="i in 3" :key="i" class="h-28 w-full" />
        </div>
        <USkeleton class="h-64 w-full" />
      </div>
    </template>

    <FormsLogicEditor />
  </FormsBuilderFrame>
</template>
