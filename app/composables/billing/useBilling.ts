/**
 * The workspace's subscription (F24) for Settings → Subscription and Plans: the overview (plan, status,
 * usage), the plans, invoices, and the change / checkout flow. One shared state so the header badge, the
 * pages and the dialogs agree after a change.
 */
import type { BillingOverview, BillingPeriod, CheckoutSession, Invoice, Plan, PlanId } from '#shared/types/billing'

const overview = ref<BillingOverview | null>(null)
const plans = ref<Plan[] | null>(null)
const invoices = ref<Invoice[] | null>(null)
const failed = ref(false)
/** The period the Plans page shows (remembered while the app is open). */
const period = ref<BillingPeriod>('monthly')
/** A checkout waiting for the processor (the dialog shows it). */
const checkout = ref<CheckoutSession | null>(null)

export function useBilling() {
  const api = useApi()
  const { handle } = useErrorHandler()

  async function load(options: { invoices?: boolean } = {}) {
    failed.value = false
    try {
      const [main, list, bills] = await Promise.all([
        api.get<BillingOverview>('/billing'),
        plans.value ? Promise.resolve(null) : api.get<Plan[]>('/billing/plans'),
        options.invoices ? api.get<Invoice[]>('/billing/invoices') : Promise.resolve(null),
      ])
      overview.value = main.data
      if (list) plans.value = list.data
      if (bills) invoices.value = bills.data
      // The Plans page starts on the period the workspace pays for
      if (main.data.subscription.current_period_end) period.value = main.data.subscription.period
    } catch (error) {
      failed.value = true
      handle(error, { silent: true })
    }
  }
  async function loadPlans() {
    if (plans.value) return
    try {
      plans.value = (await api.get<Plan[]>('/billing/plans')).data
    } catch (error) {
      handle(error, { silent: true })
    }
  }
  const set = (value: BillingOverview) => (overview.value = value)

  /** Change plan; when a payment is needed first it opens the checkout. */
  async function change(plan: PlanId, newPeriod: BillingPeriod) {
    const { data } = await api.post<{ overview: BillingOverview; checkout: { plan: PlanId; period: BillingPeriod; amount: number } | null }>('/billing/change', { plan, period: newPeriod })
    overview.value = data.overview
    if (data.checkout) checkout.value = (await api.post<CheckoutSession>('/billing/checkout', { plan, period: newPeriod })).data
    else invoices.value = null
    return !data.checkout
  }
  async function addCard() {
    checkout.value = (await api.post<CheckoutSession>('/billing/checkout', { purpose: 'add_card' })).data
  }

  const planById = (id: PlanId) => plans.value?.find(plan => plan.id === id) ?? null
  return { overview, plans, invoices, failed, period, checkout, load, loadPlans, set, change, addCard, planById }
}
