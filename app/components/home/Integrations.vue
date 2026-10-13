<script setup lang="ts">
// Integrations orbit after reference 2: logos on two slow rings around the headline; they stand still for people
// who prefer less motion. Logos from simple-icons (CLAUDE.md, allowed extras).
const { t } = useI18n()
const localePath = useLocalePath()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

const INNER = [
  { name: 'MySQL', icon: 'i-simple-icons-mysql' },
  { name: 'PostgreSQL', icon: 'i-simple-icons-postgresql' },
  { name: 'MariaDB', icon: 'i-simple-icons-mariadb' },
  { name: 'SQL Server', icon: 'i-simple-icons-microsoftsqlserver' },
  { name: 'Oracle', icon: 'i-simple-icons-oracle' },
]
const OUTER = [
  { name: 'Webhooks', icon: 'i-lucide-webhook' },
  { name: 'Google', icon: 'i-simple-icons-google' },
  { name: 'Okta', icon: 'i-simple-icons-okta' },
  { name: 'Microsoft', icon: 'i-simple-icons-microsoft' },
  { name: 'API', icon: 'i-lucide-braces' },
  { name: 'Facebook', icon: 'i-simple-icons-facebook' },
  { name: 'OpenID', icon: 'i-simple-icons-openid' },
  { name: 'SAML 2.0', icon: 'i-lucide-shield-check' },
]

/** A point on a ring, in percent of the square. */
const place = (index: number, count: number, radius: number, offset = 0) => {
  const angle = (index / count) * Math.PI * 2 + offset
  return { left: `${50 + radius * Math.cos(angle)}%`, top: `${50 + radius * Math.sin(angle)}%` }
}
</script>

<template>
  <UPageSection>
    <div
      ref="root"
      class="relative mx-auto aspect-square w-full max-w-2xl"
      :class="{ 'motion-paused': paused }"
      dir="ltr"
    >
      <!-- Rings -->
      <div aria-hidden="true" class="absolute inset-[8%] rounded-full border border-default" />
      <div aria-hidden="true" class="absolute inset-[21%] rounded-full border border-dashed border-default" />
      <div aria-hidden="true" class="absolute inset-[30%] rounded-full bg-violet-500/10 blur-3xl" />

      <!-- Outer ring turns one way, inner the other; each logo turns back so it stays upright -->
      <ul class="absolute inset-0 motion-safe:animate-orbit">
        <li
          v-for="(item, i) in OUTER"
          :key="item.name"
          class="absolute -translate-x-1/2 -translate-y-1/2"
          :style="place(i, OUTER.length, 42)"
        >
          <span
            class="flex size-11 items-center justify-center rounded-full bg-default shadow-lg shadow-black/5 ring-1 ring-default motion-safe:animate-orbit-reverse sm:size-14"
            :title="item.name"
          >
            <UIcon :name="item.icon" class="size-5 text-highlighted sm:size-6" />
            <span class="sr-only">{{ item.name }}</span>
          </span>
        </li>
      </ul>
      <ul class="absolute inset-0 motion-safe:animate-orbit-reverse">
        <li
          v-for="(item, i) in INNER"
          :key="item.name"
          class="absolute -translate-x-1/2 -translate-y-1/2"
          :style="place(i, INNER.length, 29, 0.6)"
        >
          <span
            class="flex size-10 items-center justify-center rounded-full bg-default shadow-lg shadow-black/5 ring-1 ring-default motion-safe:animate-orbit sm:size-12"
            :title="item.name"
          >
            <UIcon :name="item.icon" class="size-5 text-highlighted" />
            <span class="sr-only">{{ item.name }}</span>
          </span>
        </li>
      </ul>

      <!-- The headline in the middle -->
      <div class="absolute inset-[29%] flex flex-col items-center justify-center text-center" dir="auto">
        <p class="text-xs font-semibold text-primary sm:text-sm">{{ t('home.integrations.eyebrow') }}</p>
        <h2
          class="mt-1 text-base font-semibold tracking-tight text-balance text-highlighted sm:text-xl lg:text-2xl"
        >
          {{ t('home.integrations.title') }}
        </h2>
        <p class="mt-2 hidden text-xs text-muted lg:block">{{ t('home.integrations.description') }}</p>
        <UButton
          :to="localePath('/integrations')"
          :label="t('home.integrations.link')"
          color="neutral"
          variant="outline"
          size="sm"
          trailing-icon="i-lucide-arrow-right"
          class="mt-3 sm:mt-5"
        />
      </div>
    </div>
  </UPageSection>
</template>
