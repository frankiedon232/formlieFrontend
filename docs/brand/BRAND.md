# Formalie brand kit

The owner chose **Field F** on 2026-10-10. It's an F built from form fields, plus a dot for the answer that arrives. The same kit is used by the portal (this project), the website (`formalieSite`) and the platform admin (`formaliePlatformFront`). Copy it, don't redraw it.

## The mark

| File | Use |
| --- | --- |
| `svg/formalie-mark.svg` | Default: ink tile, white F. Light backgrounds. |
| `svg/formalie-mark-inverse.svg` | White tile, ink F. Dark backgrounds. |
| `svg/formalie-mark-accent.svg` | Ink tile with a violet dot. Marketing only (website hero, social). Never in the portal UI. |
| `svg/formalie-glyph.svg`, `formalie-glyph-white.svg` | The F alone, when the tile comes from the UI (a rounded box) |
| `svg/formalie-lockup-light.svg`, `formalie-lockup-dark.svg` | Mark and wordmark side by side (for light and dark backgrounds) |
| `png/` | The same at fixed sizes: mark 16 to 1024, the variants at 512, lockups at @2x and @4x |
| `web/` | `favicon.ico` (16, 32, 48), `favicon.svg` (follows the browser's light / dark mode), `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `site.webmanifest`, `og-image.png` (1200 × 630) |

Geometry, on a 64 grid:
- **Tile:** 64 × 64 with a corner radius of 16 (25%).
- **Bars:** 9 thick with round ends: the top bar is 34 long, the stem 34, the middle bar 22.
- **Dot:** radius 4.5, at (45, 33.5).

In code, the portal uses the glyph as an icon: `<UIcon name="i-formalie-mark" />` (`app/assets/icons/mark.svg`, `currentColor`) inside a `rounded-lg bg-inverted text-inverted` box at twice the icon size.

## Wordmark

"Formalie" in **Manrope Bold (700)**, letter-spacing −0.035em, sentence case. The lockup gap is a quarter of the mark's height. In the lockup SVGs the wordmark is live text (Manrope, with Inter or the system font as fallback). Use the PNG lockups wherever Manrope can't load (emails, documents).

## Colours

| Name | Hex | Use |
| --- | --- | --- |
| Ink | `#0a0a0a` | Tile, text, primary buttons |
| Paper | `#ffffff` | Backgrounds, the F on ink |
| Accent | `#7c3aed` | The dot in the accent mark and small highlights on the website. Never a large fill. |

## Rules

- **Clear space:** keep at least half the mark's height empty around it.
- **Minimum size:** 16 px for the mark and 96 px wide for the lockup.
- **Allowed:** the black mark on light backgrounds, the inverse on dark, and the glyph in a UI box in the current text colour.
- **Not allowed:**
  - no stretching, rotating, outlines, shadows or gradients;
  - no other colours for the tile;
  - never move the dot or change the bar lengths;
  - never set the wordmark in another font.
- **Workspaces:** a workspace's own logo appears next to Formalie, never in place of it. The sign-in hub, "Secured by Formalie" and the sidebar always show this mark.

## Regenerating

The SVGs are the sources. `node scripts/brand/render.mjs` (in formalieFrontend, with headless Chrome on port 9333) renders every PNG, the favicon and the OG image again.

## Emails

Every email Formalie sends uses one layout. The owner approved the design on 2026-10-12, and it is the same in the backend (`formlyBackend/app/modules/emails/layout.py`) and the mock (`server/mock/core/emailLayout.ts`). Examples are in `email/`.

- **Header:** an ink band (`#0a0a0a`, 18 px corners) holding:
  - the workspace's tile: a white tile with its logo or its initial, or the Field F glyph on Formalie's own emails;
  - its name, with "Sent with Formalie" underneath;
  - the **fields motif** on the end side: two pills and a dot, taken from the mark.

  The dot and a 3 px rule under the band take the workspace's brand colour. Without one, the dot is white.
- **Card:** white with a 1 px `#e7e7e5` border. The subject is the title (23 px, weight 800).
  - A line ending in a link becomes an ink button with the line's own words, with the full link under it in small text.
  - Codes sit in a large spaced box.
  - Answers go in a bordered table.
- **Footer:** centred and muted, in this order:
  1. the mark with "Formalie";
  2. the tagline;
  3. a short divider;
  4. why the person got the email;
  5. Privacy · formalie.com, plus Unsubscribe on emails people can turn off.
- **Technique:** tables and inline styles only. Light colour scheme, right to left for Arabic. The mark images come from the portal's `public/brand/`; in the backend the address is set by `EMAIL_ASSETS_URL`.
