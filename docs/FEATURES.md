# What Formalie does (source for feature pages)

Every item below exists in the app today. Use it as the source for the feature pages; don't promise anything that isn't listed here, or that is marked *later*.

## Form builder · `screenshots/form-builder(-dark).jpg`
- **Building:**
  - drag-and-drop questions into rows and pages, with a keyboard alternative for every drag;
  - undo and redo, autosave, full-screen.
- **Over 40 question types:**
  - **text:** short, long, rich text, email, phone, website, number, amount, full name, percentage;
  - **time:** date, time, date and time, date range, duration;
  - **choices:** dropdown, multi-select, single choice, checkboxes, ranking, matrix, rating, scale, slider;
  - **uploads:** file and image, signature;
  - **places and identity:** address, country, language, time zone, currency;
  - **technical:** IP address, domain, MAC address, colour, IBAN, SWIFT;
  - **other:** consent, hidden and calculated fields, and sections, paragraphs, dividers and images for layout.
- **Lists:**
  - option lists reusable in any form, with levels (Country → Region → City);
  - large lists of up to 200,000 options that load as people type;
  - details on options (price, region…) that fill other questions.
- **Saved questions** to reuse.
- **Who sees each question:** everyone, or chosen departments, roles or people.
- **Languages:** forms in several languages, with translation help.
- **Versions:** draft → publish; editing a live form opens a new draft; every publish is a version you can preview and restore.

## Logic and calculations · `screenshots/form-logic.jpg`
- **Rules:** show, hide, require or make a question optional, enable or disable it, set or clear an answer, show or hide pages, jump to a page, or skip to the end, based on earlier answers.
- **Calculations:**
  - totals, scores and prices worked out live (if, min, max, sum, average, count, days between dates, rounding);
  - a calculation may give a text ("High risk");
  - it can read a detail of the chosen option (`{product.price}`).
- **Checks** that catch mistakes before people hit them.

## Design and templates · `screenshots/form-design(-dark).jpg`, `templates.jpg`
- **Starting points** (Workspace default, Minimal, Soft, Bold, Dark, Elegant, Banner, Ribbon, Grounded, Slate accent, Aurora, Corporate).
- **What you can change:** layout, background (colour, gradient, image), container, **21 fonts** (self-hosted), colours with contrast hints, inputs, buttons, sections and blocks, header, footer and thank-you page.
- **Themes and page designs:** save them as themes and apply them to any form; page designs (landing pages) frame the form on its link.
- **Template library** by category (business and customer, HR and workplace, events and bookings, health and safety, hospitality, education …), plus saving your own forms as templates.
- **AI:** a form from a description or a document, and a theme from a brand colour.

## Sharing · `screenshots/share-channels.jpg`
- **Where people answer:** a form link, a website embed (with allowed sites), the API, or any mix of them.
- **The address:** a custom link address, a short link and a QR code.
- **Who may answer:**
  - anyone, with a password, invited people only, or signed-in people;
  - one response per person, response limits, and open and close dates;
  - people may also fill in later and continue where they stopped.
- **SEO** for form links (title, description, image, noindex).
- **Who can see this form:** everyone in the workspace, what they may do with it and why.

## Responses and analytics · `screenshots/responses(-dark).jpg`, `response-detail.jpg`, `analytics(-dark).jpg`
- **Working with responses:**
  - table and card views, search across answers, filters, date ranges, columns and sorting;
  - review statuses (new, reviewed, approved, rejected), tags, and notes in the detail panel;
  - editing answers with history.
- **Export** to Excel, CSV or PDF, with progress shown.
- **AI summary** of a response; insights across responses.
- **Analytics:** visits, starts and completions, drop-off by question, devices, channels and languages.

## Dashboard · `screenshots/dashboard-overview(-dark).jpg`, `dashboard-kpis(-dark).jpg`
- **Four views:** Workspace, Forms, Data sources and API service.
- **What they show:**
  - KPI cards with trends and the activity over time;
  - busiest forms, what needs attention, what is coming up, and recent responses.
- **Controls:** filters by folder and owner, and periods by day, week, month or year.

## Data sources · `screenshots/data-sources(-dark).jpg`, `data-connections.jpg`
- **Bring your database:**
  - MySQL, MariaDB, PostgreSQL, SQL Server and Oracle;
  - test the connection, a permissions guide, health and response time.
- **Response storage:** every response stored in your database as it arrives, in Formalie's own prefixed tables, with backfill and retries.
- **Database explorer:** browse tables, change rows in your own tables, export.
- **Query editor:** SQL with autocomplete; read-only by default; history, saved queries and exports.
- **Activity:** everything done on the connections, in the audit trail.

## API service · `screenshots/api-service(-dark).jpg`, `api-docs.jpg`
- **Endpoints:** any form becomes endpoints, grouped into services that can be switched on and off.
- **Methods:** GET (list and read), POST (create), PUT (change) and DELETE, with the fields accepted and returned chosen per endpoint.
- **Tokens:** static or short-lived tokens, test and live, with scopes.
- **Requests:** required headers, signed requests, and Formalie-Key repeat protection.
- **Protection:**
  - access rules by IP, domain, region and country, with allowed websites for browser apps;
  - rate limits per token, IP and endpoint.
- **Insight:** request logs and analytics.
- **Docs:** generated API documentation with a try-it console.
- **Webhooks** with signed deliveries and retries.

## Access and security · `screenshots/roles-access.jpg`
- **People:**
  - invites, sign-up links with approval, departments, job titles and managers;
  - roles with fine-grained permissions (own, shared or all), and your own roles;
  - folder access, per-form sharing, and "who can see this form".
- **Sign-in:** email and password, Google or Facebook on every plan; a company's single sign-on (Okta, Microsoft Entra ID, Google Workspace, OneLogin, SAML 2.0 or OpenID Connect) on paid plans; two-step sign-in (an authenticator app or text message), and session control.
- **Settings:** password rules, an allowed IP list, and session length.
- **Audit trail** of every action, with export.
- **Encryption:**
  - in transit (with end-to-end encrypted requests between the app and the server) and at rest;
  - no secrets kept in the browser.
- **Data residency:** the region your data stays in (Enterprise).

## Workspace and brand
- **Branding:** logo (and a dark version), brand colour, browser tab icon and sign-in picture.
- **Appearance of the whole portal:** colours, light and dark modes, fonts and layout.
- **Address:** your own subdomain and custom domain, plus your own sending address or mail server.
- **Settings:** company details, departments, privacy (retention, consent line, data requests) and form defaults.

## AI assistant
- **Building:** forms from a description or a document, template ideas, and a theme from a brand colour.
- **In the builder:** help with questions and logic.
- **Analysing:** response analysis, questions about your data in plain words, and summaries.
- **Translating and writing:** translation and help with wording.
- **Credits** per plan.

## Help and onboarding · `screenshots/help-centre.jpg`
- **Help centre:** articles, FAQs and a glossary in 20 languages, plus an assistant that answers from them.
- **Help in context:** "?" on every page, "Show me where", and **guided tours offered on the first visit**.
- **Onboarding:** a set-up wizard for new workspaces, and first steps on the dashboard.

## Languages
- **The app:** 20 languages, including Arabic (right to left).
- **Forms:** in several languages each, with a language switch for respondents.
- **Locale:** dates, numbers and currencies follow the person's language and region.
