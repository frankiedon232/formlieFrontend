<!-- Auth page heading: optional back link · workspace chip · large title · description. -->
<script setup lang="ts">
const props = defineProps<{
  title: string
  description?: string
  /** Show which workspace this is (tenant hosts). */
  workspace?: boolean
  back?: string
}>()
const emit = defineEmits<{ back: [] }>()
const { t } = useI18n()
const config = useRuntimeConfig()
const tenant = useTenant()
const profile = tenant.profile
</script>

<template>
  <div class="mb-8">
    <div v-if="props.back" class="mb-6">
      <UButton
        icon="i-lucide-arrow-left"
        :label="props.back"
        color="neutral"
        variant="link"
        class="-ms-1 px-1 text-muted rtl:[&_svg]:rotate-180"
        @click="emit('back')"
      />
    </div>

    <div
      v-if="props.workspace && profile?.mode === 'tenant'"
      class="mb-6 hidden max-w-full items-center gap-2.5 rounded-full lg:inline-flex bg-elevated/60 py-1 ps-1 pe-3.5 ring-1 ring-default"
    >
      <UAvatar :alt="profile.name" size="xs" class="bg-inverted text-inverted" />
      <span class="truncate text-sm font-medium text-highlighted">{{ profile.name }}</span>
      <span class="hidden truncate font-mono text-xs text-muted sm:inline">
        {{ profile.subdomain }}.{{ config.public.rootDomain }}
      </span>
      <span class="sr-only">{{ t('auth.workspace') }}</span>
    </div>

    <h1 class="text-3xl font-semibold tracking-tight text-highlighted">{{ props.title }}</h1>
    <p v-if="props.description || $slots.description" class="mt-2 text-[15px] leading-relaxed text-muted">
      <slot name="description">{{ props.description }}</slot>
    </p>
  </div>
</template>
