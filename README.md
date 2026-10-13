# formalieSite: the Formalie website

The public website of **Formalie**, a secure, flexible platform for building forms, collecting and managing data, connecting systems and controlling access, for organisations of any size, anywhere in the world.

The website presents the product and leads people into it:
- **Product story:** features, solutions, integrations and security.
- **Plans:** pricing with a Monthly / Quarterly / Annually toggle.
- **Sign-up:** the site hands over to the portal, which creates the workspace and handles checkout.
- **Sales and support:** Enterprise and support enquiries, through Formalie's own forms.
- **Legal pages:** laid out like documentation.

| | Development | Production |
|---|---|---|
| Website | `https://formalie.dev:3033/` | `https://formalie.com/` (confirm) |
| Portal (sign-in, sign-up) | `https://manage.formalie.dev:2202/` | `https://manage.formalie.com/` |
| Public form links | `https://forms.formalie.dev:2202/` | `https://forms.formalie.com/` |
| Backend API (public plans, legal, platform) | `https://formalie.dev:5004/api/v1` | `https://services.formalie.com/api/v1` |

## Start

```bash
pnpm install
pnpm dev        # https://formalie.dev:3033 (hosts entry + the dev certificate, see docs/02-DEV-ENVIRONMENT.md)
pnpm typecheck && pnpm lint && pnpm test
pnpm generate   # prerendered site for production
```

## What is in this folder

| Path | What |
|---|---|
| `CLAUDE.md` | Rules for building this project |
| `STARTUP-PROMPT.md` | The first message to give Claude Code in the new project |
| `PROGRESS.md` | Phases, tasks and logs |
| `docs/00-OVERVIEW.md` | Positioning, audience, tone, goals |
| `docs/01-ARCHITECTURE.md` | Stack, rendering, i18n, SEO, hosting |
| `docs/02-DEV-ENVIRONMENT.md` | Local setup on port 3033 |
| `docs/SITEMAP.md` | Every page and its sections |
| `docs/CONTENT.md` | The copy, page by page (English; translated into 20 languages) |
| `docs/FEATURES.md` | What the product does, area by area (source for feature pages) |
| `docs/PRICING.md` | Plans, prices (samples), periods, comparison, Enterprise |
| `docs/SIGNUP-FLOW.md` | How the site hands over to the portal |
| `docs/LEGAL-PAGES.md` | The documentation-style legal pages and their content source |
| `docs/DESIGN.md` | Look and feel, tokens, the data-flow hero, references |
| `docs/API-HOOKS.md` | What the site reads from Formalie (plans, legal, forms) |
| `docs/SEO.md` | Titles, metadata, structured data, sitemap |
| `docs/SECURITY.md` | What the site may show and how |
| `docs/design/references/` | The owner's three reference screens |
| `docs/screenshots/` | Cropped, watermarked shots of the real app for feature sections |
| `docs/reference/` | The app's data-flow animation and theme tokens, to start the hero from |
