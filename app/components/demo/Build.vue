<script setup lang="ts">
// The form builder, animated: each beat a field type lights up in the palette and drops into the form.
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')

const FIELDS = [
  { type: 'shortText', icon: 'i-lucide-type', label: 'fullName', input: 'i-lucide-user', half: false },
  { type: 'email', icon: 'i-lucide-mail', label: 'email', input: 'i-lucide-mail', half: true },
  { type: 'phone', icon: 'i-lucide-phone', label: 'phone', input: 'i-lucide-phone', half: true },
  {
    type: 'dropdown',
    icon: 'i-lucide-square-chevron-down',
    label: 'country',
    input: 'i-lucide-globe',
    half: true,
  },
  { type: 'date', icon: 'i-lucide-calendar', label: 'startDate', input: 'i-lucide-calendar', half: true },
] as const
const PALETTE = ['shortText', 'email', 'phone', 'date', 'dropdown', 'rating'] as const
const ICONS: Record<string, string> = {
  shortText: 'i-lucide-type',
  email: 'i-lucide-mail',
  phone: 'i-lucide-phone',
  date: 'i-lucide-calendar',
  dropdown: 'i-lucide-square-chevron-down',
  rating: 'i-lucide-star',
}

const { step } = useDemoLoop(root, FIELDS.length)
const shown = computed(() => FIELDS.slice(0, step.value))
const picking = computed(() => FIELDS[step.value]?.type ?? FIELDS[step.value - 1]?.type)
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('demo.form')" icon="i-lucide-file-text">
      <template #actions>
        <span
          class="hidden items-center gap-1 rounded-full bg-elevated p-0.5 text-[10px] font-medium sm:flex"
        >
          <span class="rounded-full bg-default px-2 py-0.5 text-highlighted shadow-sm">{{
            t('home.tabs.build.label')
          }}</span>
          <span class="px-2 py-0.5 text-muted">{{ t('demo.logic') }}</span>
          <span class="px-2 py-0.5 text-muted">{{ t('home.tabs.design.label') }}</span>
        </span>
        <span class="rounded-md bg-inverted px-2.5 py-1 text-[10px] font-semibold text-inverted">{{
          t('demo.publish')
        }}</span>
      </template>

      <div class="grid grid-cols-[9rem_minmax(0,1fr)] gap-4 sm:grid-cols-[10.5rem_minmax(0,1fr)]">
        <!-- Palette -->
        <div class="rounded-xl bg-elevated/40 p-2 ring-1 ring-default">
          <p class="px-1.5 pb-1.5 text-[10px] font-semibold tracking-wide text-muted uppercase">
            {{ t('demo.fields') }}
          </p>
          <ul class="space-y-0.5">
            <li
              v-for="type in PALETTE"
              :key="type"
              class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] transition-all duration-300"
              :class="picking === type ? 'bg-inverted text-inverted shadow-md' : 'text-toned'"
            >
              <UIcon :name="ICONS[type]!" class="size-3.5 shrink-0" />
              <span class="truncate">{{ t(`demo.types.${type}`) }}</span>
            </li>
          </ul>
        </div>

        <!-- The form being built -->
        <div class="min-w-0 rounded-xl p-3 ring-1 ring-default">
          <div class="flex items-center justify-between text-[10px] text-muted">
            <span>{{ t('demo.step') }}</span>
            <span>33%</span>
          </div>
          <div class="mt-1.5 h-1 overflow-hidden rounded-full bg-elevated">
            <div class="h-full w-1/3 rounded-full bg-inverted" />
          </div>
          <div class="mt-3 grid min-h-[13.5rem] grid-cols-2 content-start gap-x-3 gap-y-2.5">
            <div
              v-for="field in shown"
              :key="field.type"
              class="motion-safe:animate-pop"
              :class="field.half ? 'col-span-1' : 'col-span-2'"
            >
              <p class="mb-1 text-[11px] font-medium text-highlighted">
                {{ t(`demo.labels.${field.label}`) }} <span class="text-red-500">*</span>
              </p>
              <div class="flex h-8 items-center gap-1.5 rounded-lg px-2 ring-1 ring-default">
                <UIcon :name="field.input" class="size-3.5 text-dimmed" />
                <span class="h-1 w-1/2 rounded-full bg-elevated" />
              </div>
            </div>
            <div class="col-span-2 mt-1 flex justify-end">
              <span
                class="flex items-center gap-1 rounded-lg border border-dashed border-accented px-2 py-1 text-[10px] text-muted"
              >
                <UIcon name="i-lucide-plus" class="size-3" />{{ t('demo.addField') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </DemoWindow>
  </div>
</template>
