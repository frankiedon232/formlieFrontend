# Decisions and notes

- **The website and the app are separate projects** (owner 2026-10-10). The website is `formalieSite` (Nuxt, on port 3033 in development); the app is `formalieFrontend` (port 2202); the platform admin is `formaliePlatformFront` and `formaliePlatformBack`.
- **Addresses:** the website is at `https://formalie.dev:3033/` in development. The owner gave the same address for production; the expected production address is `https://formalie.com/`, so confirm it with the owner before launch.
- **The references are ideas, not targets** (owner): "this is just an idea, it does not cancel the screens of the app". The website follows the app's look.
- **Only the parts of the app that are needed are shown** (owner: "not all, for security"). Screens are cropped, watermarked and on sample data (`SECURITY.md`).
- **Light and dark screens are mixed** across the site (owner 2026-10-10).
- **The hero grows from the sign-in animation "in a different way"** (owner): the same idea (sources → hub → destinations), richer and larger, and the hub is **always Formalie** (owner: "my name can not diminish").
- **Legal pages look like documentation** (owner), with their text from the platform admin later; placeholders until then.
- **The links to the portal forms come later** (owner): contact, Enterprise and newsletter are Formalie's own forms, embedded, wired in phase S6.
- **No custom CSS anywhere** (owner, in the app): customers never write code, so the website doesn't promise it.
- **Prices are samples** until the owner sets them in the platform admin; the website reads them from the public plans endpoint.
- **Backend hand-over (owner, 2026-10-13):** the site reads `/public/plans`, `/public/legal`, `/public/legal/{slug}?lang=` and `/public/platform` from formlyBackend at `NUXT_PUBLIC_API_URL` (`https://formalie.dev:5004/api/v1`; production `https://services.formalie.com/api/v1`, never `api.formalie.com`, which is customers' own API service). Plain `{ success, data, meta }`, any origin. Fallback data stays for when the API doesn't answer.
- **Payments by Paddle**, the merchant of record (owner, 2026-10-13), replacing Payoneer: "Payments handled by Paddle" near the prices, no logo yet.
- **Legal pages:** seven, with `refunds` ("Refunds and cancellation") after subprocessors; first text from formlyBackend `docs/legal/`; a "Draft" note until the owner publishes each one; `/terms`, `/privacy` and `/refunds` redirect to `/legal/…`. A `/trust` page comes from `docs/legal/trust-and-security.md`, without its "Independent checks (when ready)" section for now.
- **Packages added in S0 beyond the CLAUDE.md list:** `@nuxt/image` (rule 8 requires `NuxtImg`) and `@iconify-json/lucide` (Nuxt UI's own icon set, bundled so icons render in prerendered pages without calling another site). The owner may still say no.
- **Pure helpers live in `app/utils/`** (`locales.ts`, `links.ts`), not `shared/`: Nuxt 4.5's prerender build breaks on `shared/` imports from `nuxt.config.ts` (a wrong relative path), and the website has no server code to share with.
- **Git branch:** the work is on `formalieWeb` (the branch the owner pushed on 2026-10-13); CLAUDE.md still names `formalieSite`.
