# Design references

The same images that guide the Formalie portal also guide Formalie Platform. Check this folder before building any page.

**These images are the exact target design** (owner, 2026-10-02 for Formalie, applies here too): same layout, spacing, placement and monochrome look (black primary actions). Only the product name ("Formalie Platform"), the logo and the content differ.

**Style, not features:** the images define the look and feel. Do not copy their widgets (kanban cards, "Due" pills, task charts) into screens about something else; design what the screen needs and dress it in this style.

**Same as the portal:** when in doubt, open the Formalie portal and match it. The two products should feel like one family.

| Image | Applies to | What to take from it | What to ignore |
| --- | --- | --- | --- |
| `Screenshot 2026-10-02 084447.png` | App shell, list pages (Workspaces, Accounts, Staff, Articles) | Far-left icon rail + grouped sidebar with count badges; navbar search with `Ctrl/⌘K` hint, notifications, primary action top-right; page title + meta line; KPI cards; filter chip + Sort + Table / Grid view switch; cards grid | "Relatio" name/logo, task content |
| `Screenshot 2026-10-02 092034.png` | Overview, Analytics reports, DataView tables | KPI row with trend badges, date range + Daily / Weekly / Monthly segmented control, chart card with tooltip, side detail card, table with selection, sortable headers, status badges, slim bars, row action menu | "Relatio" name/logo, task content |

Add a row for every new image.

## How the shell maps to the design

| Design | Formalie Platform |
| --- | --- |
| Rail: ⋯ · black + · workspace avatars | `AppSidebarRail`: more menu · Create (new article, announcement, message, plan draft) · area icons (Overview, Analytics, Workspaces, Billing, Content, Defaults, Operations, Staff) |
| Brand + « collapse | `AppSidebarMenu` header with the Formalie mark (`i-formalie-mark`, `docs/brand/`) and "Formalie Platform" (« = collapse, `[`) |
| MAIN MENU with dots and counts | the active area's menu (for example Workspaces → All / Active / Trial / Suspended / Closed with counts) |
| RESOURCES (+) | saved reports, saved segments |
| SYSTEM: Dark Mode switch, Settings, Help | same, plus Audit trail and Approvals (badge with pending count) |
| User card (avatar, name, email, ⇅) | `AppUserMenu` with the staff member's role |
| Top bar: search left; bell, avatars, Add right | search left (`Ctrl/⌘+K`, workspaces, accounts, articles, pages); language, approvals bell, notifications; page primary action |
| Title + "Last sync" line + Import / Add (black) | `AppPanel` header: title + meta line (for example "Data as of 2 min ago") + outline / solid actions |
| Segmented controls | `SEGMENTED_UI` on every view switch and on Daily / Weekly / Monthly in reports |
