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

| Workspace    | Person                                 | Email                              | Use it to test                                                                     |
| ------------ | -------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------- |
| Remedy Legal | Frankie Don, workspace owner           | `admin@remedylegal.test`           | Normal sign-in; code by email or SMS; sees the **Audit trail**                     |
| Remedy Legal | Marcus Reid, account disabled by admin | `marcus.reid@remedylegal.test`     | Correct password, but "Account disabled. Contact your administrator."              |
| Remedy Legal | Lena Novak, staff member (Reviewer)    | `staff@remedylegal.test`           | **Form test:** opening a form set to "Only my organisation" (Share tab), see below |
| Samath Tax   | Elena Rossi, workspace owner           | `admin@samathtax.test`             | Sign-in with Google, Apple and Facebook buttons shown                              |
| Both         | James Carter, external consultant      | `james.carter@carterpartners.test` | Member of both workspaces; **Find my workspace** lists both; no audit trail access |
| Old Co       | ,                                      | ,                                  | Suspended workspace page (`https://oldco.formalie.dev:2202/`, needs a hosts entry) |

**Where to sign in**

| Address                                  | What you get                                    |
| ---------------------------------------- | ----------------------------------------------- |
| `https://remedylegal.formalie.dev:2202/` | Remedy Legal sign-in                            |
| `https://samathtax.formalie.dev:2202/`   | Samath Tax sign-in                              |
| `https://manage.formalie.dev:2202/`      | Find my workspace · Create a workspace (signup) |

**Form test, "Only my organisation" (F10):** as the owner, open a published form → **Share** → _Who can open the form_ → **Only my organisation** → Save. Open the form's link in a private window: it says "Only for members of Remedy Legal" → **Sign in to Remedy Legal** → sign in as `staff@remedylegal.test` → you come back to the form with "Filling in as Lena Novak (staff@remedylegal.test)". Each member can respond once. Someone without a Remedy Legal account (e.g. `admin@samathtax.test`) can't sign in there, so never reaches the form. Put the form back to _Anyone with the link_ afterwards.

**Form test, "Only invited people" (F10):** invitations need no account, any valid email works (development sends no mail; the Share tab shows each person's personal link to copy). Paste these into _Invitations_:

```
test1@example.org, test2@example.org, test3@example.org
```

Open a personal link in a private window → "Filling in as test1@example.org"; the plain form link says "This form is by invitation only". Check the status (Invited → Opened → Responded), that a second response from the same link is refused, and that **Revoke** stops a link. To see invalid-address checking, add `not-an-email`, it turns red and blocks sending. Put the form back to _Anyone with the link_ afterwards.

**Form test, people access "Can view" (F10):** as the owner, open a form → **Share** → _Your team_ → _People with access_ → add Lena Novak → **Can view** → Save. Sign in as `staff@remedylegal.test`: the form's overview shows **Preview** (no Edit, no Save as template, no Share settings, no availability change), and editor addresses (`/build`, `/design`, `/logic`, `/share`, `/versions`) say "Only people who can edit open the editor".

**Form test, forms in several languages (F10):** in the editor, **Form settings** → _More languages_ → add e.g. Français (the built-in dictionaries fill in what they know) → **Translate** to fill in the rest → Publish. Open the form link: the switcher sits at the top of the form and the address gets `?lang=fr`; `…/fill?lang=fr` opens French directly. Without `?lang=` the form always opens in its main language (Form settings → Form language), whatever the browser's language. Change a question afterwards: its translation shows "Changed since translated". **Preview** (form overview) shows the form in a phone, tablet or desktop frame with the same switcher.

**Responses (F11):** open any published form → **View responses** (or **Responses** in the sidebar for all forms). Seeded forms have sample responses (stable, international sample people); your own test submissions appear there too, numbered after them, and in the form overview's trend. Try the period (7 / 30 / 90 days, 12 months), click a status in _Review status_ to filter, switch to **Summary**, pick question **Columns**, open a response and use **J** / **K**, change its status, add a tag and a note.

**One-time code:** after the password, the code screen shows the mock's code in dev ("Development code: 123456"). It is also printed in the dev-server console as `[mock-otp]`. Five wrong codes lock the attempt.

**Without a hosts entry** (e.g. `localhost` or a phone on Wi-Fi): add `?tenant=remedylegal` once, e.g. `https://localhost:2202/auth/login?tenant=remedylegal` (dev only, remembered for the tab).

Workspaces created through signup live until the dev server restarts.

**People and roles (F16 + F22):** every account above signs in with the same password. Roles are per workspace (People → Roles & access): **Owner** (built in, everything, locked), **Admin** (everything except Roles & access), **Member** (builds and publishes forms, works with responses; no People, Data, API, Settings or Audit), plus roles you make. A role change applies from the person's next sign-in.

| Person (Remedy Legal)  | Email                             | Role                            | Use it to test                                                                                                   |
| ---------------------- | --------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Frankie Don            | `admin@remedylegal.test`          | Owner                           | Everything: People, Roles & access, Add user, Sign-up links, approvals                                           |
| Sofia Martins          | `sofia.martins@remedylegal.test`  | Admin                           | Manages people and the workspace, but no Roles & access                                                          |
| Alex Novak             | `alex.novak@remedylegal.test`     | Admin                           | Same as Sofia                                                                                                    |
| Priya Raman            | `priya.raman@remedylegal.test`    | Member                          | Forms and responses only                                                                                         |
| Lukas Becker           | `lukas.becker@remedylegal.test`   | Member                          | Same as Priya                                                                                                    |
| Kenji Watanabe         | `kenji.watanabe@remedylegal.test` | Member                          | Same as Priya                                                                                                    |
| Lena Novak             | `staff@remedylegal.test`          | Reviewer (own role, local data) | Forms view only, Responses view and export; no People, Data, API, AI, Settings, Audit, Analytics; no New form   |
| Amara Okafor           | `amara.okafor@remedylegal.test`   | Member (local data)             | Was made with **Add user** and activated from the activation link                                               |
| Kenji Sato             | `kenji.sato@example.org`          | Member (local data)             | Signed up with the workspace's sign-up link, then approved                                                       |
| Marcus Reid            | `marcus.reid@remedylegal.test`    | Disabled                        | Sign-in is refused                                                                                               |

"Local data": the Reviewer role and the last two accounts were made while testing and live in this machine's `.data/mock/` (not in the seed). On a fresh checkout make them again with the steps below.

**Test your own account with a role:**

1. Sign in as the owner (`admin@remedylegal.test`) → **People**.
2. Add yourself, either way:
   - **Add user** (N): your details and a role → you're _Not activated_. Development sends no mail: in your panel use ⋯ → **Copy activation link**, open it in a private window, choose your password, sign in.
   - **Sign-up links** → switch the workspace's link on → open it in a private window → fill in your details → "Request sent". Signing in now says the account waits for approval. As the owner: **People → Awaiting approval** → open yourself → **Approve** (pick role, departments, job titles, manager). Now you can sign in.
3. As the owner, **People → Roles & access**: make a role (or edit one) and tick what it may view, create, edit, delete, export or manage per area; picking an action ticks the view it needs. Give it to yourself (your panel → **Edit** → Role).
4. Sign out, sign in as yourself: the rail, menus, pages and buttons follow the role; an address the role doesn't open shows **No access**, and the API refuses it too.

## API service: test cases (F13)

Sign in as `admin@remedylegal.test` (password above) and open **API service** in the rail. Everything below runs against the mock (`NUXT_PUBLIC_API_MOCK=true`), which answers real HTTP calls, so Postman works too. Setup for Postman (address, certificate, files): [docs/02-DEV-ENVIRONMENT.md → API service from Postman](docs/02-DEV-ENVIRONMENT.md).

**Addresses.** The API address is shown in **API Documentation** (`https://api.formalie.dev/{key}/…`). From Postman use `https://localhost:2202/public-api/{key}/{endpoint}` (or `https://api.formalie.dev:2202/…` with a hosts entry).

**Mock-only headers** (they stand in for what the real service reads from the connection): `X-Forwarded-For: 203.0.113.9` sets the caller's IP, `X-Debug-Country: GB` its country, `X-Debug-Network: vpn` (or `proxy`, `tor`, `hosting`) its anonymous network.

### 1. Guided setup, from nothing to a live endpoint

1. **New service** (rail **+** → _New API service_, or Services → New service). Step 1 explains what a service is and shows the five setup steps; step 2 asks for the name; step 3 says it is ready and that an endpoint comes next. Click **Create an endpoint**: the wizard opens with the service already chosen.
2. **No service yet:** in a workspace without services, _Endpoints → New endpoint_ shows "Create a service first" with a **New service** button; creating one there brings you straight back to the wizard.
3. **New endpoint:** the page explains what an endpoint is (Got it hides that). Pick a published form, name, methods, questions. The review step says it is created **not live**. After **Create endpoint** the page shows _Before it goes live_: service and form, a token, who may call (optional), test, go live.
4. **Token for this endpoint** (from that list): the token dialog opens with the name and _What it may call_ already set to this endpoint. Choose **Test**, create it, copy the token. The last step says what comes next.
5. **Test it:** _Try it_ on the list (or API Documentation) sends a call with a test token. It works although the endpoint is not live yet.
6. **Go live:** switch it on in the list. A live token is needed for real calls; until there is one, the list says so.
7. The endpoint's panel keeps showing _Before it goes live_ until it is live with a live token. The Overview shows the five steps until one endpoint is live with a live token.

Expected API answers along the way: a **live** token on a not-live endpoint gets `503 FRM-API-1007` (`endpoint: not_live`); a **test** token gets through (and nothing is stored).

### 1b. A form for the API only

1. Open a form → **Share** → _Where people can answer_ → **API only** → Save changes. The link, short link, embed and access cards disappear; the overview says "API only".
2. Open its link, its `…/embed` address and its short link in a private window: each says the form was not found (like a form that does not exist).
3. A **draft** form: _New endpoint_ lists it under _Not ready for the API yet_ with **Publish for the API only**. One click makes it API only, publishes it and picks it.
4. Turn the API off for a form that has an endpoint: calls answer `503 FRM-API-1007` (`form: not_for_api`) and the endpoint checklist says why.
5. Change a form that has an endpoint: rename a question (Publish says nothing changes for apps), then add a required question and Publish: the dialog lists the endpoint and says the new key is now required. After publishing, the docs show the new question.
6. Every endpoint speaks label names: in Docs, the panel and the wizard you see `first_name`, not `first_name_w6r3`; send the old key and the answer refuses it by that name. Rename an API name in the endpoint wizard's Questions step.
7. New questions get clean keys (`first_name`); a second "First name" gets `first_name_2`. After publishing, renaming a question keeps its key.

### 2. Tokens

1. **New token** first asks **How it signs in** (no default): _Bearer token_ or _Client id and secret_. It is named after what it may call (pick one endpoint: "Account Service · /account"; one service: "Account Service token"; type your own any time). It shows four steps: kind (live or test, bearer or client id + secret) → name and what it may call (a sentence sums it up) → expiry → the token.
2. **See it again later:** open the token's panel → _Secret_ → **Show** → enter your password. A wrong password says how many tries are left; five wrong tries lock it for 15 minutes. The right one shows the token with Copy for 60 seconds, then it hides again. The audit trail records _API token viewed_.
3. Tokens made before this change can't be shown again ("Rotate it to get one you can view later"); rotate them once.
4. Rotate (old secret keeps working for the chosen grace time), Revoke (calls get `401`), Delete (only once revoked or expired).
5. Webhook tokens (type _For webhooks_) are tokens too: seen again, rotated and revoked the same way.

### 3. Access rules

1. **New rule:** step 1 explains what rules do, Allow or Block, and the type: IP address, Website domain, Country, Region, **Anonymous networks** (VPN, open proxy, Tor, hosting and cloud).
2. **Chips:** for IPs type `203.0.113.5, 999.1.1.1 198.51.100.0/24`: comma, space or Enter turns each into a chip; `999.1.1.1` stays in the box in red ("isn't an IP address or range") until you fix it. Backspace in the empty box takes the last chip back. Domains work the same (`example.com`, `*.example.com`).
3. Country and Region show how the country is found (from the IP; VPN users appear in the VPN's country) and point to Anonymous networks.
4. **Test a caller** (header button): pick an endpoint, an IP, a website, a country and networks, and see whether it gets in and which rule decided.
5. From Postman, with a block rule on `vpn`: send `X-Debug-Network: vpn` → `403 FRM-API-1015` (`blocked: vpn`).

### 4. API Documentation

1. Wide screens: the navigation on the left (Getting started, every endpoint with its methods in colour: GET green, POST violet, PUT amber, DELETE red), the part on screen marked as you scroll; click to jump. Smaller screens: a sliding row of endpoints.
2. Each method: what it does, the questions with type, required and allowed values (or the query options), and on the right the code (curl, JavaScript, Python, PHP, C#; Copy) and the answers it can give (200 / 201, 401, 422, 404, 429).
3. **Try it** opens a drawer: method buttons in colour, the address with a record id box, Body (line numbers, the form's real values) and Headers (the token and Content-Type filled in and locked; on POST a fresh `Formalie-Key` each time, _Keep this key_ to send it again and see the first record come back). **Send** (or Ctrl / ⌘ + Enter) shows status, time, size, the JSON or the answer's headers, and the last calls.
4. **Download OpenAPI** and import it into Postman (Import → file).

### 5. Every failure has a clear answer (Postman)

**Two ways to sign in, never both.** A token is a _Bearer token_ (send it as `Authorization: Bearer …`) or a _Client id and secret_ (POST them to `…/token`, then send the short-lived `access_token` as Bearer). API Documentation and each endpoint's example say which way that endpoint's token uses and show the `/token` step when needed.

**Headers, and no others:** every call sends `Authorization: Bearer <token>` and `Content-Type: application/json`. **POST** also sends `Formalie-Key: <a new unique id>` (required; in Postman `{{$guid}}` makes a new one per send). On GET, PUT and DELETE the key is optional (checked if you send one). The key: 16 to 100 letters, digits and `. _ : -`, not a simple pattern (`1111…`, `abab…`, `1234…`). The same key and body within 24 hours answer with the first record (`meta.replayed`); the same key with a different body is refused. Every answer tells the token's expiry: the `Formalie-Token-Expires` header and `meta.token_expires_at` / `meta.token_expires_in_days` next to the data.

Use a live token unless the row says otherwise. Each answer is JSON `{ "error": { "code", "message", "details" } }` with an `X-Request-Id` header.

| Try this                                                                | Expected                                                           |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Wrong address key `…/public-api/NOPE123456/job-applications`            | `404 FRM-API-1006` (`address_key`)                                 |
| Endpoint that doesn't exist                                             | `404 FRM-API-1006` (`endpoint`)                                    |
| Extra path part `…/job-applications/a/b`                                | `404 FRM-API-1006` (`path`)                                        |
| No `Authorization`, a wrong token, `Basic …`, a revoked token           | `401 FRM-API-1010`                                                 |
| Endpoint whose service is switched off                                  | `503 FRM-API-1007` (`service`)                                     |
| Endpoint that isn't live, live token                                    | `503 FRM-API-1007` (`endpoint: not_live`)                          |
| A method the endpoint doesn't answer, `PATCH`, or POST to `…/{id}`      | `405 FRM-API-1008`                                                 |
| Token limited to other methods, services or endpoints                   | `403 FRM-API-1009`                                                 |
| POST without `Formalie-Key`                                             | `400 FRM-API-1011` (`Formalie-Key: missing`)                       |
| `Formalie-Key` under 16 characters (`1234567890`), on any method       | `400 FRM-API-1011` (`Formalie-Key: short`)                         |
| `Formalie-Key` a simple pattern (`1234567890123456`, `aaaabbbbaaaabbbb`) | `400 FRM-API-1011` (`Formalie-Key: weak`)                          |
| POST again with the same key and a different body (within 24 hours)    | `409 FRM-API-1020` (`Formalie-Key: used_for_another_body`)         |
| POST the same answers again with a **new** key (any key order)        | `409 FRM-RESP-1005` (`same_answers`), as on the form's web page   |
| Form with an identity email (Form settings): POST that email again      | `409 FRM-RESP-1006` (masked email and date); a typo-close email is saved and flagged _possible duplicate_ |
| GET, PUT or DELETE without `Formalie-Key`                               | works (`200`): the key is optional there                           |
| Broken JSON, or a JSON list instead of an object                        | `400 FRM-GEN-1001`                                                 |
| Body over 1 MB                                                          | `413 FRM-API-1018`                                                 |
| A question the endpoint doesn't accept                                  | `422 FRM-API-1014` (`not_accepted`)                                |
| Missing required answers or a wrong email (the form's own rules)        | `422 FRM-RESP-1001` (per question)                                 |
| `PUT` / `DELETE` / `GET` on a record id that doesn't exist              | `404 FRM-API-1013`                                                 |
| File upload for a question that doesn't take files                      | `422 FRM-API-1014`                                                 |
| Blocked IP (`X-Forwarded-For`), range, website (`Origin`) or network    | `403 FRM-API-1015` (the matching value)                            |
| Client secret or client id sent as `Authorization: Bearer`             | `401 FRM-API-1010` (`client_credentials`: go to `/token` first)    |
| A bearer token sent to `POST …/token` (as secret or header)             | `401 FRM-API-1010` (`bearer_token`: send it as Bearer instead)     |
| Client id + wrong secret on `POST …/token`                              | `401 FRM-API-1010`                                                 |
| More than the rate limit in a minute (per IP 120 by default)            | `429 FRM-GEN-1029` with `Retry-After`                              |

And the good paths: list (`GET`), one record (`GET …/{id}`), create (`POST` with `Formalie-Key`; the same key and body again within 24 hours return the first record with `meta.replayed`), change (`PUT`), delete (`DELETE`).

### 6. Files through the API

1. Tick a file question as accepted in the endpoint wizard.
2. `POST …/{endpoint}/files?field={question key}` with Body → form-data, key `file` (type File) → `201` with an `id`. A `.exe` gets `422 FRM-RESP-1001` (`file_type`).
3. Send the id in the JSON: `"cv_resume": ["<id>"]`.

### 7. Webhooks

**What a webhook is.** When something happens to a response (it is sent, changed, reviewed or deleted), Formalie calls an address of yours with the details, so your own system hears about it straight away. You choose the address, the events and the forms.

**How your system knows the call is really from Formalie.** Every call carries the same headers as an API call, and nothing else:

```
Authorization: Bearer <webhook token>
Content-Type: application/json
Formalie-Key: dlv_…
```

- The **webhook token** is a token of the type _For webhooks_, kept in **API service → Tokens & headers** like your other tokens (see it again with your password, rotate it, revoke it). Your system must refuse any call whose `Authorization` is not exactly `Bearer <that token>`. A webhook token can never call the API, so if it leaks, nothing is exposed.
- The **Formalie-Key** is the delivery's id. If Formalie has to send the same delivery again (your system did not answer), it keeps the same Formalie-Key, so your system can see it already handled it.

#### Testing webhooks on your computer

The project comes with a small **test receiver** that plays the part of "your system": `pnpm webhook:listen` (file `scripts/webhook-receiver.mjs`, nothing to install). It listens on `http://localhost:4000/hooks`, prints every call it gets, and behaves like a real receiver must:

- it **will not start without the webhook token**;
- a call **without the token or with a wrong one is refused** (`401`, the body is not even read);
- a call it **already handled** (same Formalie-Key) is answered but not handled twice.

You need **two terminals**: one running the portal (`pnpm dev`, as usual), one for the receiver. The commands below are for **PowerShell** (the default terminal on Windows). In Git Bash, macOS or Linux, write them as shown in the note under each one.

**Step 1 · Make the webhook in the portal**

1. Open **API service → Webhooks → New webhook**.
2. **Name:** anything, e.g. `Local test`.
3. **Address:** `http://localhost:4000/hooks` (plain `http://localhost` is only allowed while developing; real webhooks need a public `https://` address).
4. **Events:** tick the ones you want to see, e.g. all four.
5. **Forms:** _Every form_ (or pick some).
6. **Webhook token:** leave **A new webhook token**. Formalie makes one for this webhook and names it after it ("Local test · webhook"). You can also pick a webhook token you made before in Tokens & headers.
7. Click **Create webhook**. A window shows the new token **once**. Click Copy.
   Lost it? **Tokens & headers → Local test · webhook → Secret → Show** (asks for your password).

**Step 2 · Start the test receiver with that token** (in the second terminal, inside the project folder)

```bash
$env:WEBHOOK_TOKEN="formalie_hook_live_..."; pnpm webhook:listen
```

Git Bash / macOS / Linux: `WEBHOOK_TOKEN=formalie_hook_live_... pnpm webhook:listen`

You should see: `Webhook receiver on http://localhost:4000/hooks (token required)`.
If you see `WEBHOOK_TOKEN is required…`, the token was not set: run the line again with your token pasted between the quotes.
Port 4000 taken? Run `$env:PORT="4100"` first and use `http://localhost:4100/hooks` as the address in Step 1.

**Step 3 · Send a test**

In the portal, open the webhook (Webhooks list → Local test) and click **Send a test**. The panel shows _Delivered · 200_, and the receiver prints:

```
#1 5:27:12 PM  POST /hooks
  token         valid
  event         ping
  Formalie-Key  dlv_2OBaQabeRLqRsM3MAn84Qn5FHYQ
  { …the JSON… }
  answered      200
```

**Step 4 · Try each event**

| Do this in the portal (or with Postman)                               | The receiver shows                                     |
| --------------------------------------------------------------------- | ------------------------------------------------------ |
| Fill in a form, or POST to one of its endpoints                       | `response.created`                                     |
| Change an answer of a response                                        | `response.updated`                                     |
| Change a response's status in Responses                               | `response.status_changed`, with `previous_status`      |
| Delete a response                                                     | `response.deleted`                                     |
| Webhook set to some forms only: fill in a form that is not one of them | nothing (correct: that form is not listened to)       |

The answers come with the same clean names as the API (`first_name`, `email_address`, …).

**Step 5 · See what happens when your system fails**

Stop the receiver (Ctrl + C) and start it so it answers every call with an error:

```bash
$env:FAIL="500"; pnpm webhook:listen
```

(The token is still set in this terminal. Git Bash / macOS / Linux: `WEBHOOK_TOKEN=... FAIL=500 pnpm webhook:listen`.)

Fill in a form once, then in the portal open the webhook → **Deliveries**:

- the delivery shows as **retrying**; Formalie tries again after 1, 5, 15, 60 and 360 minutes;
- every retry reaches the receiver with the **same Formalie-Key** as the first try;
- **Retry now** sends it again at once; **Send again** sends a finished one as a new delivery;
- after several failures in a row the webhook **pauses itself** and the panel says so (nothing is lost: switch it back on, then send the deliveries again).

Back to normal: Ctrl + C, then

```bash
Remove-Item Env:FAIL; pnpm webhook:listen
```

**Step 6 · Check that a wrong token is refused**

Stop the receiver and start it with a made-up token:

```bash
$env:WEBHOOK_TOKEN="formalie_hook_live_wrong"; pnpm webhook:listen
```

Click **Send a test**: the receiver prints `token WRONG: refused` and answers `401`, and the portal shows the delivery as failed. That is exactly what a real receiver must do with a call that does not carry its token. Start it again with the right token afterwards.

Also try: **Tokens & headers → Local test · webhook → Revoke**. The webhook's panel then warns that its token is gone, and deliveries fail with _No usable token_ until you pick another token (webhook → Edit → Webhook token).

**What Formalie keeps:** every delivery in the webhook's **Deliveries**, with each try, the request it sent (the token shown masked, personal answers masked) and your system's answer.

**If something does not work**

| You see                                                    | Why, and what to do                                                                                   |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `WEBHOOK_TOKEN is required…` when starting the receiver     | The token was not set. Run the Step 2 line with your token between the quotes.                        |
| Receiver prints `token WRONG` for real deliveries           | The token you started it with is not this webhook's token. Copy it again (Tokens & headers → Show).   |
| Portal: _The connection was refused_                        | The receiver is not running, or listens on another port than the webhook's address.                   |
| Portal: _No usable token_                                   | The webhook's token was revoked, expired or deleted. Webhook → Edit → pick or make another token.     |
| Nothing arrives                                             | The webhook is switched off, does not listen to that event, or is set to other forms.                 |

### 8. Logs

**Request logs and Analytics:** every call above appears with status, code, time, token and caller; Analytics and the Overview count them.

## Checks

```bash
pnpm typecheck && pnpm lint && pnpm test
```

While `pnpm dev` runs, use `pnpm typecheck:dev` (does not regenerate `.nuxt`).
