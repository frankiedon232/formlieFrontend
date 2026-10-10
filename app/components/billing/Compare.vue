<!--
  Every plan side by side (F24), grouped by area: a tick, a dash or the plan's limit in each cell. Scrolls
  sideways on phones, with the feature names kept in view.
-->
<script setup lang="ts">
import type { Plan, PlanFeature, PlanId } from '#shared/types/billing'

const props = defineProps<{ plans: Plan[]; current: PlanId | null }>()
const { t } = useI18n()
const { number } = useFormat()

type Cell = boolean | string
interface Row {
  key: string
  cell: (plan: Plan) => Cell
}
const has = (feature: PlanFeature) => (plan: Plan) => plan.features.includes(feature)
const limit = (value: number | null) => (value === null ? t('billing.unlimited') : number(value))
const GROUPS = computed<{ key: string; rows: Row[] }[]>(() => [
  {
    key: 'forms',
    rows: [
      { key: 'forms', cell: plan => limit(plan.limits.forms) },
      { key: 'responses', cell: plan => limit(plan.limits.responses_per_form) },
      { key: 'languages', cell: plan => t('billing.upTo', { n: plan.limits.languages }) },
      { key: 'templates', cell: has('templates') },
      { key: 'lists', cell: has('lists') },
      { key: 'themes', cell: has('themes') },
      { key: 'versions', cell: has('versions') },
      { key: 'folders', cell: has('folders') },
      { key: 'fillLater', cell: has('fillLater') },
    ],
  },
  {
    key: 'insight',
    rows: [
      { key: 'analytics', cell: has('analytics') },
      { key: 'visits', cell: has('visits') },
      { key: 'ai', cell: plan => (plan.limits.ai_credits === null ? t('billing.customAmount') : t('billing.credits', { n: number(plan.limits.ai_credits) })) },
    ],
  },
  {
    key: 'data',
    rows: [
      ...(['mysql', 'postgresql', 'mariadb', 'sqlserver', 'oracle'] as const).map(engine => ({ key: `db.${engine}`, cell: (plan: Plan) => plan.limits.databases.includes(engine) })),
      { key: 'explorer', cell: has('explorer') },
      { key: 'query', cell: has('query') },
      { key: 'destinations', cell: has('destinations') },
    ],
  },
  {
    key: 'api',
    rows: [
      { key: 'api', cell: has('api') },
      { key: 'webhooks', cell: has('webhooks') },
      { key: 'apiDocs', cell: has('apiDocs') },
    ],
  },
  {
    key: 'brand',
    rows: [
      { key: 'branding', cell: has('branding') },
      { key: 'subdomain', cell: has('subdomain') },
      { key: 'customDomain', cell: plan => (plan.limits.custom_domains === 0 ? false : plan.limits.custom_domains === null ? t('billing.unlimited') : number(plan.limits.custom_domains)) },
      { key: 'customEmail', cell: plan => plan.limits.custom_email },
      { key: 'customCss', cell: plan => plan.limits.custom_css },
    ],
  },
  {
    key: 'access',
    rows: [
      { key: 'emailSignin', cell: () => true },
      { key: 'socialSignin', cell: plan => plan.limits.social_signin },
      { key: 'sso', cell: plan => plan.limits.sso },
    ],
  },
  {
    key: 'support',
    rows: [
      { key: 'helpCentre', cell: () => true },
      { key: 'prioritySupport', cell: has('prioritySupport') },
      { key: 'dedicatedSupport', cell: has('dedicatedSupport') },
      { key: 'securityReview', cell: has('securityReview') },
    ],
  },
])
const rowLabel = (key: string) => (key.startsWith('db.') ? t('billing.compare.db', { name: t(`billing.${key}`) }) : t(`billing.compare.${key}`))
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-default">
    <table class="w-full min-w-[44rem] text-sm">
      <thead class="sticky top-0 bg-default">
        <tr class="border-b border-default">
          <th class="sticky start-0 bg-default px-4 py-3 text-start font-medium text-muted">{{ t('billing.compare.title') }}</th>
          <th v-for="plan in props.plans" :key="plan.id" class="px-4 py-3 text-center font-semibold" :class="plan.id === current ? 'text-highlighted' : 'text-default'">
            {{ t(`billing.plan.${plan.id}.name`) }}
            <span v-if="plan.id === current" class="block text-[11px] font-normal text-success">{{ t('billing.yours') }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in GROUPS" :key="group.key">
          <tr class="bg-elevated/50">
            <th :colspan="props.plans.length + 1" class="sticky start-0 px-4 py-2 text-start text-[11px] font-medium text-muted uppercase">{{ t(`billing.compare.group.${group.key}`) }}</th>
          </tr>
          <tr v-for="row in group.rows" :key="row.key" class="border-b border-default last:border-b-0">
            <th scope="row" class="sticky start-0 bg-default px-4 py-2.5 text-start font-normal text-default">{{ rowLabel(row.key) }}</th>
            <td v-for="plan in props.plans" :key="plan.id" class="px-4 py-2.5 text-center">
              <template v-if="typeof row.cell(plan) === 'string'"><span class="text-default tabular-nums">{{ row.cell(plan) }}</span></template>
              <UIcon v-else-if="row.cell(plan)" name="i-lucide-check" class="size-4 text-success" :aria-label="t('billing.included')" />
              <UIcon v-else name="i-lucide-minus" class="size-4 text-dimmed" :aria-label="t('billing.notIncluded')" />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
