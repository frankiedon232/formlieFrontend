# Design

## The references (`design/references/`)

They are **ideas for layout and feel**, not targets to copy. Take from them:

| Reference | Take | Don't take |
|---|---|---|
| `01-shopwave-landing.png` | Split hero: headline and two buttons on the left, product cards floating on the right with small stat chips around a chart · the "Trusted by" logo strip · "What sets us apart" feature cards with an icon tile, title and two lines | Blue buttons, their logos, "Backed by Y Combinator" |
| `02-deflexai-sections.webp` | Centred hero with **logos orbiting on rings** around the headline (use it for Integrations) · white sections with soft gradient blobs · alternating text and product-card blocks · a tidy multi-column footer · small notification cards stacking | Their brand, purple |
| `03-codivoo-products.webp` | **Product tabs** with a big card showing a product (title, description, key features with checkmarks, two buttons, a screenshot) · stat tiles (10,000+ · 45% · 99.9%) · a feature grid with mini charts inside cards | Coral and red, their stats (use only true numbers) |

## Formalie's look (the same as the app)

- **Ink:** monochrome. Actions are black in light mode and white in dark mode. Text is near-black (`neutral-950`), muted text is `neutral-600`, and borders are `neutral-200`.
- **Font:** Manrope (300 to 700). Headlines 600 with tight tracking: 56 to 64 px on desktop, 36 to 40 px on phones. Body 16 to 18 px.
- **Radius:** 0.5rem for controls, 1rem for cards, 1.5rem for big panels. Soft shadows (`shadow-xl shadow-black/5`).
- **Colour:** used only for status (green, amber, red, violet) and for **one** soft glow per section (violet or neutral, as in the sign-in panel). Never blue, orange or coral as a brand colour.
- **Light and dark:** both are designed. Dark sections (the security band, the hero panel) use `neutral-950` with a faint grid and a glow, as in `screenshots/signin-flow.jpg`.
- **Tokens:** copy the `@theme` block from `reference/main.css.excerpt` (fonts, `float`, `drift`, `dash` animations, `rise` entrance).

## The hero: "data on the move", the website version

The portal's sign-in panel shows a hub with sources on the left and destinations on the right, with points of light travelling through it (`reference/AuthFlow.vue`, `screenshots/signin-flow.jpg`). The website builds a **bigger and richer variant**:

1. **Layout:** after reference 1. Headline on the left: "Forms, data and access, under your control." The subline and **Start free** and **Talk to sales** sit below it. On the right sits the animation, in a large dark panel with the grid and a glow.
2. **Sources (left):**
   - Form link, Website embed, QR code, API, and one more, "Mobile app" (calls the API).
   - Each is a small **live card** rather than a pill, showing a mini form field being filled ("Name: Amara O…" typing), an embed frame or a QR.
3. **The hub (centre):** **always the Formalie mark** (owner: the product's name never shrinks), with the lock and "Encrypted on the way". It gives a soft pulse each time data passes.
4. **Destinations (right):**
   - Your database (with the five engine logos cycling), Webhooks, Dashboard (a tiny bar chart that grows a bar on each arrival), Email alerts, Formalie storage.
   - They light up as data arrives.
5. **Floating response cards** drift up behind the hub and fade, from the first owner concept: answers being collected.
6. **Counters** under the panel tick up softly: "responses collected", "sent to your database", "countries", all clearly labelled as illustrative.
7. **Phones:** the panel stacks under the text, with three sources, the hub and three destinations, flowing top to bottom.
8. **Built with SVG and CSS only** (animateMotion, CSS keyframes), no video and no library. Everything stands still with `prefers-reduced-motion`, and it pauses when off screen (`IntersectionObserver`).

## Using the screenshots

- Show them **inside a device or card frame** (browser chrome with three dots, rounded, a soft shadow), slightly rotated or overlapped like the floating cards in reference 1, never full-bleed.
- Use them at their real crop. Never stretch them, and don't remove the watermark.
- Pick light or dark to match the section: dark sections use the `-dark` versions where one exists.
- Convert them to WebP in `public/screenshots/` with `NuxtImg` sizes `sm:100vw md:50vw lg:640px`. Alt text says what the screen shows ("The form builder: questions on the left, the form in the middle, settings on the right").

## Section patterns

- **Feature card:** icon tile (black square, white icon), title, two lines, and an optional "Learn more →".
- **Product tab card** (reference 3): tabs with an icon and a name; the card has a title, a paragraph, 4 checkmark points, a primary and an outline button, and the screenshot on the right.
- **Stat tiles:** a big number with a small caption. Use only true facts (20 languages, 5 databases, 4 ways to collect).
- **Integrations orbit** (reference 2): database and tool logos on two slow rings around a headline. They stand still with reduced motion.
- **Call to action:** a dark rounded panel with a headline, a line, and two buttons.
- **FAQ:** `UAccordion`, one open at a time.

## Brand

Use the kit in `docs/brand/` (BRAND.md has the rules):
- the mark, inverse and accent variants, plus the lockups for the header and footer;
- `web/` for the favicons, manifest and OG image.

The accent mark (violet dot) is for the hero and social images only.
