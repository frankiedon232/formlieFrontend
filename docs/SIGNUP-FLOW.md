# Sign-up and sign-in from the website

The website never creates accounts or takes payments itself. It sends people to the **portal**, which already has the sign-up, verification, workspace creation and (with F24) checkout.

| Button | Goes to (development / production) |
|---|---|
| Start free | `https://manage.formalie.dev:2202/auth/signup?plan=starter` / `https://manage.formalie.com/auth/signup?plan=starter` |
| Start with Professional / Business | `…/auth/signup?plan=professional&period=annually` (the chosen period) |
| Sign in | `https://manage.formalie.dev:2202/auth/find-workspace` / `https://manage.formalie.com/auth/find-workspace` (they type their email and get their workspace) |
| Talk to sales / Contact us (Enterprise) | `/enterprise#enquiry` on the website (the embedded Enterprise form) |

Build the links with a `useSiteLinks()` composable reading `NUXT_PUBLIC_PORTAL_URL`, never written inline.

## What the portal does with `plan` and `period` (to add in the app, F24 "sign-up with checkout")

1. Sign-up: account, then email code, then the workspace, as today.
2. Starter, or no plan: the workspace opens on Starter.
3. Professional or Business: after the workspace is created, Settings → Plans opens the checkout for that plan and period (Paddle, the merchant of record). If they close it, the workspace stays on Starter, and a banner offers to finish.
4. The website shows the same plan names, prices and periods as the portal: both read the platform's plans.

## The sign-in page look

The portal's sign-in and sign-up pages have the "data on the move" panel (`docs/screenshots/signin-flow.jpg`, source in `docs/reference/AuthFlow.vue`). The website hero is built from the same idea **in its own way** (`DESIGN.md`), so moving from the website to sign-up feels like one product.
