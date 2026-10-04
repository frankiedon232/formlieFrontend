# Formalie, portal frontend

A secure, flexible platform for creating forms, collecting and managing data, connecting systems and controlling access, built for organisations of any size, anywhere in the world.

Nuxt 4 · Nuxt UI 4 · Tailwind 4 · TypeScript · pnpm.

- **Progress and roadmap (every task, per phase):** [PROGRESS.md](PROGRESS.md)
- **Rules for development:** [CLAUDE.md](CLAUDE.md)
- **Design references:** [docs/design/README.md](docs/design/README.md)

## Run

```bash
cp .env.example .env
pnpm install
pnpm dev --host 0.0.0.0 --port 2202 --https --https.cert=C:\devcerts\formalie.pem --https.key=C:\devcerts\formalie-key.pem
```

Open `https://manage.formalie.dev:2202/` (default entry) or `https://{workspace}.formalie.dev:2202/`.
Hosts file, wildcard certificate and backend setup: [docs/02-DEV-ENVIRONMENT.md](docs/02-DEV-ENVIRONMENT.md).
After `pnpm add` / `pnpm install`, **restart `pnpm dev`** (postinstall regenerates `.nuxt`).

## Test accounts (mock API)

The mock API (`NUXT_PUBLIC_API_MOCK=true`) is seeded in [server/mock/data/tenants.ts](server/mock/data/tenants.ts). These are **test values for local development only**, they exist only in the dev server's memory and never reach a real backend.

**Password for every account:** `Formalie!2026`

| Workspace    | Person                                  | Email                              | Use it to test                                                                     |
| ------------ | --------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- |
| Remedy Legal | Frankie Don, workspace owner           | `admin@remedylegal.test`           | Normal sign-in; code by email or SMS; sees the **Audit trail**                     |
| Remedy Legal | Marcus Reid, account disabled by admin | `marcus.reid@remedylegal.test`     | Correct password, but "Account disabled. Contact your administrator."              |
| Remedy Legal | Lena Novak, staff member               | `staff@remedylegal.test`           | **Form test:** opening a form set to "Only my organisation" (Share tab), see below |
| Samath Tax   | Elena Rossi, workspace owner           | `admin@samathtax.test`             | Sign-in with Google, Apple and Facebook buttons shown                              |
| Both         | James Carter, external consultant      | `james.carter@carterpartners.test` | Member of both workspaces; **Find my workspace** lists both; no audit trail access |
| Old Co       |,                                       |,                                  | Suspended workspace page (`https://oldco.formalie.dev:2202/`, needs a hosts entry) |

**Where to sign in**

| Address                                  | What you get                                    |
| ---------------------------------------- | ----------------------------------------------- |
| `https://remedylegal.formalie.dev:2202/` | Remedy Legal sign-in                            |
| `https://samathtax.formalie.dev:2202/`   | Samath Tax sign-in                              |
| `https://manage.formalie.dev:2202/`      | Find my workspace · Create a workspace (signup) |

**Form test, "Only my organisation" (F10):** as the owner, open a published form → **Share** → *Who can open the form* → **Only my organisation** → Save. Open the form's link in a private window: it says "Only for members of Remedy Legal" → **Sign in to Remedy Legal** → sign in as `staff@remedylegal.test` → you come back to the form with "Filling in as Lena Novak (staff@remedylegal.test)". Each member can respond once. Someone without a Remedy Legal account (e.g. `admin@samathtax.test`) can't sign in there, so never reaches the form. Put the form back to *Anyone with the link* afterwards.

**Form test, "Only invited people" (F10):** invitations need no account, any valid email works (development sends no mail; the Share tab shows each person's personal link to copy). Paste these into *Invitations*:

```
test1@example.org, test2@example.org, test3@example.org
```

Open a personal link in a private window → "Filling in as test1@example.org"; the plain form link says "This form is by invitation only". Check the status (Invited → Opened → Responded), that a second response from the same link is refused, and that **Revoke** stops a link. To see invalid-address checking, add `not-an-email`, it turns red and blocks sending. Put the form back to *Anyone with the link* afterwards.

**Form test, people access "Can view" (F10):** as the owner, open a form → **Share** → *Your team* → *People with access* → add Lena Novak → **Can view** → Save. Sign in as `staff@remedylegal.test`: the form's overview shows **Preview** (no Edit, no Save as template, no Share settings, no availability change), and editor addresses (`/build`, `/design`, `/logic`, `/share`, `/versions`) say "Only people who can edit open the editor".

**Form test, forms in several languages (F10):** in the editor, **Form settings** → *More languages* → add e.g. Français (the built-in dictionaries fill in what they know) → **Translate** to fill in the rest → Publish. Open the form link: the switcher sits at the top of the form and the address gets `?lang=fr`; `…/fill?lang=fr` opens French directly. Without `?lang=` the form always opens in its main language (Form settings → Form language), whatever the browser's language. Change a question afterwards: its translation shows "Changed since translated". **Preview** (form overview) shows the form in a phone, tablet or desktop frame with the same switcher.

**Responses (F11):** open any published form → **View responses** (or **Responses** in the sidebar for all forms). Seeded forms have sample responses (stable, international sample people); your own test submissions appear there too, numbered after them, and in the form overview's trend. Try the period (7 / 30 / 90 days, 12 months), click a status in *Review status* to filter, switch to **Summary**, pick question **Columns**, open a response and use **J** / **K**, change its status, add a tag and a note.

**One-time code:** after the password, the code screen shows the mock's code in dev ("Development code: 123456"). It is also printed in the dev-server console as `[mock-otp]`. Five wrong codes lock the attempt.

**Without a hosts entry** (e.g. `localhost` or a phone on Wi-Fi): add `?tenant=remedylegal` once, e.g. `https://localhost:2202/auth/login?tenant=remedylegal` (dev only, remembered for the tab).

Workspaces created through signup live until the dev server restarts.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test
```

While `pnpm dev` runs, use `pnpm typecheck:dev` (does not regenerate `.nuxt`).
