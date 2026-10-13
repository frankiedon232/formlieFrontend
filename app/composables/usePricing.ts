import type { PricingPlanProps } from '@nuxt/ui'

/**
 * The pricing page's shared state and wording (docs/PRICING.md): the chosen period, and each plan as Nuxt UI
 * shows it (cards and the comparison table's header use the same numbers).
 */
export function usePricing() {
  const { t, locale } = useI18n()
  const localePath = useLocalePath()
  const links = useSiteLinks()
  const { plans, source } = usePlans()
  const period = useState<Period>('pricing-period', () => 'annually')

  const money = (amount: number, currency: string) => formatPrice(amount, currency, locale.value)

  /** Price, billing line and button of one plan for the chosen period. */
  const offer = (plan: Plan) => {
    const name = t(`home.pricing.plans.${plan.id}`)
    if (!plan.prices) {
      return {
        title: name,
        description: t('pricingPage.enterpriseTagline'),
        price: t('pricingPage.custom'),
        billingPeriod: t('pricingPage.enterpriseBilling'),
        button: {
          label: t('pricingPage.contactUs'),
          to: `${localePath('/enterprise')}?plan=enterprise&period=${period.value}#enquiry`,
          color: 'neutral' as const,
          variant: 'outline' as const,
        },
      }
    }
    const perMonth = pricePerMonth(plan, period.value)!
    const free = plan.prices.monthly === 0
    const saving = savingPercent(plan, period.value)
    return {
      title: name,
      description: t(`home.pricing.taglines.${plan.id}`),
      price: free ? t('home.pricing.free') : money(saving ? plan.prices.monthly : perMonth, plan.currency),
      discount: !free && saving ? money(perMonth, plan.currency) : undefined,
      // One line under the price: "per month · Billed $182.40 every year".
      billingPeriod: free
        ? t('pricingPage.freeForever')
        : `${t('home.pricing.perMonth')} · ${
            period.value === 'monthly'
              ? t('pricingPage.billed.monthly')
              : t(`pricingPage.billed.${period.value}`, {
                  amount: money(plan.prices[period.value], plan.currency),
                })
          }`,
      badge: plan.recommended
        ? t('home.pricing.mostPopular')
        : saving
          ? t('pricingPage.save', { percent: saving })
          : undefined,
      highlight: plan.recommended,
      button: {
        label: free ? t('nav.startFree') : t('home.pricing.startWith', { plan: name }),
        to: links.signup(plan.id, period.value),
        color: 'neutral' as const,
        variant: plan.recommended ? ('solid' as const) : ('outline' as const),
      },
    } satisfies PricingPlanProps
  }

  return { plans, source, period, offer, money }
}
