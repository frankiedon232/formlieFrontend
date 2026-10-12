# Start-up prompt for the formalieSite project

Paste this as the first message in Claude Code, opened in `C:\UNETPROJECTS\formalieSite`:

---

You are building **formalieSite**, the public website of Formalie. Before anything else, read these files:
- `CLAUDE.md`, `README.md`, `PROGRESS.md`;
- `docs/00-OVERVIEW.md`, `docs/01-ARCHITECTURE.md`, `docs/02-DEV-ENVIRONMENT.md`;
- `docs/SITEMAP.md`, `docs/DESIGN.md`, `docs/CONTENT.md`, `docs/FEATURES.md`, `docs/PRICING.md`;
- `docs/SIGNUP-FLOW.md`, `docs/LEGAL-PAGES.md`, `docs/API-HOOKS.md`, `docs/SEO.md`, `docs/SECURITY.md`.

Then look at:
- every image in `docs/design/references/` (the owner's ideas for layout and feel);
- `docs/screenshots/` (cropped, watermarked shots of the real app, light and dark);
- `docs/reference/AuthFlow.vue`, the app's "data on the move" animation that the website hero grows from.

Rules that matter most:
- **Stack:** Nuxt 4.5 with Nuxt UI 4. Nuxt UI components first, Tailwind for layout only.
- **Look:** the same as the Formalie app (Manrope, monochrome ink, black or white actions).
- **Copy:** 20 languages, Arabic right to left, no em dashes, global and neutral.
- **Claims:** no invented facts, numbers or customer logos.
- **Security:** only the provided screenshots (or new ones made the same way), and only Formalie's own embedded forms for collecting data.
- **Legal pages** look like documentation, with text from the platform admin API (placeholders until then).

Work through `PROGRESS.md` phase by phase, starting with **S0**. Tick tasks and log progress as you go, commit and push after each verified milestone, and stop for my review at the end of each phase. Ask before adding any package that `CLAUDE.md` doesn't list.

---
