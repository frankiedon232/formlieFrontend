# Design references

Images that guide the look and feel of the Formalie portal. Claude Code checks this folder before building pages.

**These images are the exact target design** (owner, 2026-10-02): same layout, spacing, placement and monochrome look (black primary actions). Only the product name/logo and the domain content differ.

**Style, not features** (owner, 2026-10-02): the images define the *look and feel*. Do not copy their widgets (kanban cards, “Due” pills, task charts) into screens that are about something else — design what the screen needs and dress it in this style.

| Image | Applies to | What to take from it | What to ignore |
| --- | --- | --- | --- |
| `Screenshot 2026-10-02 084447.png` | App shell, list pages (Tasks) | Far-left icon rail + grouped sidebar (Main menu / Resources / System) with count badges; navbar search with `⌘K` hint, notifications, avatars, primary action top-right; page title + "last sync" line; KPI cards; filter chip + Sort + Table/Kanban/Timeline view switch; cards grid | "Relatio" name/logo, task domain content (we show forms) |
| `Screenshot 2026-10-02 092034.png` | Dashboard (F19), DataView table | KPI row with trend badges, date-range + Daily/Weekly/Monthly segmented control, chart card with tooltip, side detail card, table with checkbox selection, sortable headers, status badges, progress bars, row action menu | "Relatio" name/logo, task domain content |

Add a row for every new image.

## How the shell maps to the design (F1)

| Design | Formalie |
| --- | --- |
| Rail: ⋯ · black + · workspace avatars | `AppSidebarRail`: more menu · Create (new form / from template) · workspaces (org switcher in F3); collapsed → section icons + » + avatar |
| Brand + « collapse | `AppSidebarMenu` header (« = collapse, `[`) |
| MAIN MENU: Tasks → To-do / In progress / In review / Completed (dots, counts) | Forms → All / Drafts / Published / Closed (dots; counts in F5), Responses, Analytics, Integrations |
| RESOURCES (+) with coloured folders | Templates, Option sets, Themes |
| SYSTEM: Dark Mode switch, Settings, Help & Support | same |
| User card (avatar, name, email, ⇅) | `AppUserMenu` |
| Top bar: search left; bell, avatars, Add Member right | search left (`Ctrl/⌘+K`); language, bell, New form right (team avatars arrive with Users, F16) |
| Title + "Last sync" line + Import / Add (black) | `AppPanel` header: title + meta line + outline / solid actions |
| Segmented controls (Table / Kanban / Timeline, Daily / Weekly, Week 1 / 2) | `SEGMENTED_UI` on every view switch: grey track, active option white with hairline + soft shadow |

## How the builder maps to the style (F7, no dedicated image)

| Style element | Builder |
| --- | --- |
| Header title + "Last sync: Just now" | inline form name · status badge · "Saved just now" |
| Outline secondary + black primary buttons | undo / redo / Preview (outline) · Publish (black) |
| Muted uppercase group labels + icon rows (sidebar) | field palette categories |
| White cards, hairline borders, small outline icon buttons (⋯) | the page card; selected field = dark outline with a type pill and drag / duplicate / delete / ⋯ |
| Side detail card | inspector |
| Segmented control | page tabs, field width, preview device |
