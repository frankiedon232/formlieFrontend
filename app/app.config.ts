export default defineAppConfig({
  ui: {
    colors: {
      // primary is monochrome ink (main.css), as in the app; violet is the one soft accent (docs/DESIGN.md).
      primary: 'neutral',
      secondary: 'violet',
      neutral: 'zinc',
    },

    // One rhythm for the whole site (owner 2026-10-13: tighter spacing, closer to the header, nicer cards).
    // Headlines are 600 with tight tracking (docs/DESIGN.md); cards are 1rem radius and lift softly on hover.
    pageHero: {
      slots: {
        container: 'flex flex-col lg:grid pt-8 pb-12 sm:pt-12 sm:pb-16 lg:pt-14 lg:pb-20 gap-10 sm:gap-y-14',
        headline: 'mb-3',
        title: 'text-4xl sm:text-5xl lg:text-6xl text-pretty tracking-tight font-semibold text-highlighted',
        description: 'text-base sm:text-lg text-muted',
        body: 'mt-8',
        footer: 'mt-8',
      },
    },
    pageSection: {
      slots: {
        container: 'flex flex-col lg:grid py-12 sm:py-16 lg:py-20 gap-8 sm:gap-12',
        headline: 'mb-2',
        title: 'text-3xl sm:text-4xl text-pretty tracking-tight font-semibold text-highlighted',
        description: 'text-base sm:text-lg text-muted',
        body: 'mt-6',
        footer: 'mt-6',
      },
    },
    pageCard: {
      slots: {
        root: 'relative flex rounded-2xl transition duration-300 hover:shadow-xl hover:shadow-black/5 motion-safe:hover:-translate-y-0.5',
        container: 'relative flex flex-col flex-1 lg:grid gap-x-8 gap-y-3 p-5 sm:p-6',
        leading: 'inline-flex items-center mb-3',
        title: 'text-base text-pretty font-semibold text-highlighted',
        description: 'text-sm/6 text-pretty text-muted',
      },
    },
    // Plan cards: nothing is cut off (names, billing lines and features wrap), the billing line sits under the
    // price, and the struck-through monthly price stays small.
    pricingPlan: {
      slots: {
        root: 'relative grid rounded-2xl p-6 xl:p-7 gap-6',
        titleWrapper: 'flex flex-wrap items-center gap-x-3 gap-y-1',
        title: 'text-highlighted text-2xl text-pretty font-semibold tracking-tight',
        description: 'text-muted text-sm text-pretty mt-2',
        priceWrapper: 'flex flex-wrap items-baseline gap-x-2 gap-y-1',
        price: 'text-highlighted text-4xl font-semibold tracking-tight',
        discount: 'text-dimmed line-through text-lg',
        billing: 'flex flex-col min-w-0 basis-full',
        billingPeriod: 'text-toned text-xs font-medium',
        billingCycle: 'text-muted text-xs font-medium',
        feature: 'flex items-start gap-2 min-w-0',
        featureTitle: 'text-muted text-sm text-pretty',
      },
    },
    pricingTable: {
      slots: {
        tierPrice: 'text-highlighted text-2xl xl:text-3xl font-semibold tracking-tight',
        tierDiscount: 'text-dimmed line-through text-base',
        tierBillingCycle: 'text-muted text-xs font-medium whitespace-nowrap',
      },
    },
    pageCTA: {
      slots: {
        container: 'flex flex-col lg:grid px-6 py-12 sm:px-12 sm:py-16 lg:px-16 lg:py-20 gap-8 sm:gap-12',
        title: 'text-3xl sm:text-4xl text-pretty tracking-tight font-semibold',
      },
    },
  },
})
