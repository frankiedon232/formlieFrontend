# CLAUDE.md, formalieSite (the Formalie website)

Read `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/SITEMAP.md`, `docs/DESIGN.md` and `docs/CONTENT.md` before starting any task. Work through the phases in [`PROGRESS.md`](PROGRESS.md) in order and tick tasks there when done.

**Keep docs in sync.** `PROGRESS.md` is the single progress tracker: every task per phase, the overview table, the new-requests log and the progress log. At every milestone:
- tick the task, add a progress-log line, and update the overview table and "Last updated";
- put any new request into the right phase **and** the new-requests log straight away;
- update every doc whose facts changed;
- **commit and push** after each verified milestone (typecheck, lint and tests green);
- stop for review at the end of each phase.

**Brand:** the Formalie mark (Field F, chosen by the owner on 2026-10-10), the wordmark, favicons, web icons and OG image are in `docs/brand/` (rules in `docs/brand/BRAND.md`). Use these files as they are: copy `docs/brand/web/*` to `public/`, and never redraw the mark or use another logo.

**Design references:** `docs/design/references/` holds the owner's three reference screens, and `docs/screenshots/` holds cropped, watermarked shots of the real Formalie app. The references set the **layout, rhythm and feel** (open white space, soft shadows, floating product cards, logo strip, feature grids, product tabs, a clean footer). They are ideas, not pixel targets. The look must match the Formalie app: monochrome ink, Manrope, the same radius and shadows (`docs/DESIGN.md`). Never copy their brands, logos, wording or colours (orange, blue, coral).

## Stack (fixed)

- **Core:** Nuxt 4.5 · Nuxt UI 4 · Tailwind CSS 4 · Vue 3.5 · TypeScript (strict) · pnpm.
- **Allowed extras:** `@nuxtjs/i18n` (20 languages, the same list as the app), `@nuxt/content` (legal pages and long copy), `@vueuse/nuxt`, `zod`, `@iconify-json/circle-flags` (language flags) and `@iconify-json/simple-icons` (integration logos).
- Ask before adding anything else.
- **Rendering:** server-side rendered or prerendered for SEO, never client-only.

**Addresses:** development `https://formalie.dev:3033/`, production `https://formalie.com/` (confirm with the owner).

The app lives elsewhere:
- portal sign-in: `https://manage.formalie.dev:2202/` in development, `https://manage.formalie.com/` in production;
- API: `https://api.formalie.dev/` in development, `https://api.formalie.com/` in production.

## Hard rules

1. **Nuxt UI first.** Build every UI from Nuxt UI components (`UHeader`, `UPageHero`, `UPageSection`, `UPageGrid`, `UPageCard`, `UPricingPlans`, `UPricingTable`, `UPageCTA`, `UFooter`, `UContentNavigation`, `UContentToc`, `UAccordion`, `UTabs`, `UMarquee` …). Use Tailwind utilities for layout only. No hand-written component styling that Nuxt UI already provides.
2. **Never import composables or components:** Nuxt auto-imports them.
3. **Mobile first:** every section works on phone, tablet and desktop.
4. **Every user-facing string is translated** in all 20 languages (`i18n/locales/`). English is the fallback. Layouts work right to left for Arabic: use logical utilities (`ms-` / `me-` / `ps-` / `pe-` / `start-` / `end-`).
5. **Global and neutral.** Formalie serves organisations of any size, anywhere:
   - examples and names are international;
   - phone examples use reserved fictional ranges (+44 7700 900xxx);
   - no country-specific imagery;
   - compliance wording promises **controls**, never certifications Formalie doesn't hold;
   - no customer logos or numbers until the owner provides real ones (use neutral placeholders such as "Trusted by teams in N countries" only when true).
6. **No em dashes** in copy or code comments: use a comma, full stop or colon.
7. **Security:** the website never shows the whole app.
   - Only the cropped, watermarked shots in `docs/screenshots/` (or newer ones made the same way).
   - No internal URLs, ids or data in pictures.
   - No secrets in the site.
   - All forms on the site (contact, enterprise, newsletter) are **Formalie's own published forms**, shown embedded (`docs/API-HOOKS.md`), never a hand-made form that posts somewhere.
8. **Fast:** Lighthouse 95+ on mobile.
   - Images through `NuxtImg` (WebP or AVIF, sized), with no layout shift.
   - The hero animation is SVG and CSS only, and still for people who prefer reduced motion.
9. **Accessible:** keyboard reachable, visible focus, real headings in order, alt text, AA contrast.
10. **SEO:** every page has a title, description, Open Graph and Twitter image, canonical URL and `hreflang` for the 20 languages. Plus a sitemap, `robots.txt` and structured data (Organization, SoftwareApplication, FAQ, Product with offers).
11. **Legal pages** (Privacy policy, Terms and conditions, Data protection, Cookie policy, Acceptable use) look like documentation: a left section navigator, the article, an "on this page" table of contents, and a last-updated date. Their content comes from the platform admin API later (`docs/LEGAL-PAGES.md`). Until then, show clearly marked placeholder text, never invented legal wording.
12. **Theme switch:** light, dark or system, in the header.

## Folder conventions

```
app/
  app.vue  app.config.ts  assets/css/main.css (Tailwind + Nuxt UI + @theme tokens only)
  layouts/   default.vue (header + footer) · legal.vue (docs layout)
  pages/     index · features/[slug] · solutions/[slug] · pricing · integrations · security · enterprise · contact · about · blog/ · legal/[slug] · changelog
  components/ site/ (Header, Footer, LanguageSwitch) · home/ · features/ · pricing/ · legal/ · flow/ (the data-flow hero)
  composables/ usePlans · useLegal · useSiteLinks
content/     (nuxt/content: blog, changelog, fallback legal placeholders)
i18n/        locales/{20 codes}.json
public/      screenshots/ (copied from docs/screenshots, WebP) · og/ · favicon
```

## Git

This project is the branch `formalieSite` of https://github.com/frankiedon232/formlieFrontend (one branch per project, like `formalieFrontend` and `formalieBackend`). Commit and push there after each verified milestone: `git push origin formalieSite`.

## Going live

`docs/PRODUCTION-CHECKLIST.md` (the same file in all five Formalie projects) lists everything that changes for production. Whenever you add a setting, key, address or service that differs between development and production, add it there, in every project's copy. Before any production deployment, walk the owner through it.
