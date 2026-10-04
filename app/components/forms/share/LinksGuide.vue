<!--
  Share → "How your form's links work" (owner, 2026-10-04): the three addresses of a form side by
  side — original (always works), custom (readable), short (posters, SMS, QR) — what each is for,
  that they all work together (none cancels another), and the everyday situations. Shows the form's
  real links; the situations fold open.
-->
<script setup lang="ts">
import type { FormShareSettings, FormSummary } from '#shared/types/forms'
import { formLink, publicHosts, shortLink } from '#shared/utils/urls/public'

const props = defineProps<{ settings: FormShareSettings; form: FormSummary }>()
const { t } = useI18n()
const config = useRuntimeConfig().public
const request = useRequestURL()
const tenant = useTenant()

const hosts = computed(() => publicHosts(config, request.port))
const sub = computed(() => tenant.profile.value?.subdomain ?? null)
const links = computed(() => [
  {
    key: 'original',
    icon: 'i-lucide-key-round',
    url: formLink(hosts.value, props.form.public_key, 'fill', sub.value),
    set: true,
  },
  {
    key: 'custom',
    icon: 'i-lucide-link-2',
    url: props.settings.custom_link ? formLink(hosts.value, props.settings.custom_link, 'fill', sub.value) : null,
    set: !!props.settings.custom_link,
  },
  {
    key: 'short',
    icon: 'i-lucide-scissors',
    url: props.settings.short_link ? shortLink(hosts.value, props.settings.short_link.code) : null,
    set: !!props.settings.short_link,
  },
])
const situations = ['shared', 'changed', 'removed', 'poster', 'closed'] as const
const open = ref(false)
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-4 sm:p-5' }">
    <div class="mb-3 flex items-start gap-3">
      <UIcon name="i-lucide-signpost" class="mt-0.5 size-5 shrink-0 text-muted" />
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('share.guide.title') }}</h2>
        <p class="text-xs text-muted">{{ t('share.guide.desc') }}</p>
      </div>
    </div>

    <!-- The three links, each with what it is for and this form's real address. -->
    <div class="grid gap-2 md:grid-cols-3">
      <div v-for="link in links" :key="link.key" class="flex min-w-0 flex-col gap-1.5 rounded-md border border-default bg-elevated/40 p-3">
        <div class="flex items-center justify-between gap-2">
          <span class="flex items-center gap-1.5 text-sm font-medium text-highlighted">
            <UIcon :name="link.icon" class="size-4 text-muted" />{{ t(`share.guide.${link.key}.name`) }}
          </span>
          <UBadge
            :label="link.key === 'original' ? t('share.guide.always') : link.set ? t('share.guide.on') : t('share.guide.off')"
            :color="link.set ? 'success' : 'neutral'"
            variant="subtle"
            size="sm"
          />
        </div>
        <p class="text-xs text-toned">{{ t(`share.guide.${link.key}.for`) }}</p>
        <code v-if="link.url" class="truncate text-[11px] text-muted" dir="ltr" :title="link.url">{{ link.url }}</code>
      </div>
    </div>

    <p class="mt-3 flex items-start gap-2 rounded-md bg-elevated/60 px-3 py-2 text-xs text-highlighted">
      <UIcon name="i-lucide-shield-check" class="mt-0.5 size-4 shrink-0 text-success" />{{ t('share.guide.together') }}
    </p>

    <!-- Everyday situations. -->
    <UButton
      :label="t('share.guide.situations')"
      :trailing-icon="open ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
      color="neutral"
      variant="link"
      size="sm"
      class="mt-2 px-0"
      :aria-expanded="open"
      @click="open = !open"
    />
    <ul v-if="open" class="mt-1 flex flex-col gap-2">
      <li v-for="situation in situations" :key="situation" class="flex items-start gap-2 text-xs">
        <UIcon name="i-lucide-corner-down-right" class="mt-0.5 size-3.5 shrink-0 text-muted" />
        <span>
          <span class="font-medium text-highlighted">{{ t(`share.guide.case.${situation}.when`) }}</span>
          <span class="text-toned"> — {{ t(`share.guide.case.${situation}.then`) }}</span>
        </span>
      </li>
    </ul>
  </UCard>
</template>
