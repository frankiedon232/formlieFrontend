# Screenshots of the Formalie app

These are made from the real app, with the rules from `docs/SECURITY.md`:
- desktop 1440 wide at 2x;
- cropped to one part;
- the Formalie watermark baked in;
- sample data only: no real keys, test names, people, logos or photos (logos and photos show as an "N" monogram).

Files ending in `-dark` are the same screen in dark mode.

| File | Shows | Use for |
|---|---|---|
| `dashboard-overview(-dark).jpg` | Activity overview chart with its tooltip | Home product tabs, the Dashboard and Analytics pages |
| `dashboard-kpis(-dark).jpg` | The dashboard's KPI cards | Home hero strip, the Dashboard page |
| `form-builder(-dark).jpg` | Builder: question palette, a multi-page form, settings with languages | Build tab, Form builder page |
| `form-design(-dark).jpg` | Designer: starting points and a live form preview | Design tab, Design page |
| `form-logic.jpg` | Rules and calculations | Logic section |
| `share-channels.jpg` | Where people can answer (link, embed, API) | Sharing, "Answers from everywhere" |
| `templates.jpg` | Template categories as cards | Templates page, solution pages |
| `responses(-dark).jpg` | Responses list with the review-status chart | Responses tab and page |
| `response-detail.jpg` | One response: status bar, facts, AI summary, grouped answers | Responses page |
| `analytics(-dark).jpg` | Conversion overview | Analytics page |
| `data-sources(-dark).jpg` | Data sources overview: KPIs, database traffic, connection health | Data tab, Data sources page |
| `data-connections.jpg` | Connections list (MySQL, PostgreSQL, SQL Server …) with status and uptime | Integrations page |
| `api-service(-dark).jpg` | API service overview: KPIs, traffic, endpoint overview | API tab, API service page |
| `api-docs.jpg` | Generated API reference | Developers solution, API service page |
| `roles-access.jpg` | Roles and access: people per role, kinds | Access and security page |
| `help-centre.jpg` | Help centre home | Help and onboarding |
| `signin-flow.jpg` | The portal's sign-in panel with the data-flow animation | Starting point for the website hero (`DESIGN.md`) |

To make new ones, run the capture tool in the formalieFrontend project (`scripts/site-screenshots/`: headless Chrome, a sample-data replacement map, a watermark; see its README). Never take a full-page screenshot of the app by hand.
