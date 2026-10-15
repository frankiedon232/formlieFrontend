# Single sign-on: step by step for each choice

How to set up single sign-on (SSO) for a workspace, and how its people then sign in on the workspace's own address. A workspace picks one of **three choices** (owner, 2026-10-15): Microsoft Entra ID, Google Workspace, or SAML 2.0 for every other provider (Okta, OneLogin, JumpCloud, ADFS, PingOne, Auth0, Keycloak and so on all speak SAML 2.0). For the owner's end-to-end test: **three workspaces, one per choice**. The same steps are what a customer's IT admin does in production (Part 6 lists the differences).

| # | Choice | Protocol | Free test account | Workspace in this guide |
| --- | --- | --- | --- | --- |
| 1 | Microsoft Entra ID | OpenID Connect | your Azure / Entra tenant | `ssoentra` |
| 2 | Google Workspace | SAML 2.0 | Google Workspace (14-day trial; needs an admin) | `ssogoogle` |
| 3 | SAML 2.0 (Okta, OneLogin and any other provider) | SAML 2.0 | Mock SAML (no account), Okta Integrator Free Plan, OneLogin developer account | `ssosaml` |

The subdomain names are suggestions; use any you like and replace them below.

**How it works.** Formalie is the "service provider" (the app). The identity provider (Okta, Microsoft and so on) knows the people and their passwords. When someone presses "Continue with …" on `https://{workspace}.formalie.dev:2202/auth/login`, Formalie sends them to the provider; the provider checks who they are and sends them back to Formalie, which signs them in. In development everything works on your own machine: the providers only redirect your browser, they never need to reach `formalie.dev` themselves.

---

## Part 0. Before you start (once)

1. ⬜ **The dev stack is running**: the backend (`scripts\dev-up.ps1`) and the portal (`pnpm dev` on 2202).
2. ⬜ **Hosts file.** Windows can't do wildcard names, so add one line per workspace to `C:\Windows\System32\drivers\etc\hosts` (open Notepad as administrator):
   ```
   127.0.0.1   ssoentra.formalie.dev
   127.0.0.1   ssogoogle.formalie.dev
   127.0.0.1   ssosaml.formalie.dev
   ```
   The mkcert certificate already covers `*.formalie.dev`.
3. ⬜ **Email domains.** Single sign-on is tied to the email domain of the people who use it (for example `northwind.com`). Each part below says which domain its test people will have. Sign up each workspace's **owner with an email outside that domain** (your usual address), so the owner can always sign in with a password while you experiment.

## Part 1. Create the three workspaces and give them a paid plan

Single sign-on is on the Professional, Business and Enterprise plans. Payments (B15) aren't connected yet, so a development command moves a workspace to a paid plan the way the platform admin will.

For each workspace:

1. ⬜ Go to `https://manage.formalie.dev:2202/auth/signup`, sign up with your own email (Google, Facebook or email and password), and choose the subdomain (`ssoentra` and so on). Finish the setup steps.
2. ⬜ In PowerShell, in `C:\UNETPROJECTS\formlyBackend`:
   ```
   fmly\Scripts\python.exe scripts\dev_set_plan.py ssoentra
   ```
   It prints `ssoentra is now on business`. Repeat with each subdomain. Reload the portal.
3. ⬜ In the workspace: **Settings → Sign-in → Single sign-on** is now available (no upgrade prompt).

## Part 2. The Formalie side (the same for every choice)

Open **Settings → Sign-in → Single sign-on** in the workspace and pick **Microsoft Entra ID**, **Google Workspace** or **SAML 2.0**. The screen has three steps:

- **Step 1, "In {provider}, add Formalie":** Formalie's own values, each with a Copy button. You paste these into the provider (Parts 3 to 5 say where):
  - Microsoft Entra ID (OpenID Connect): **Sign-in redirect address** `https://{workspace}.formalie.dev:2202/api/v1/auth/sso/oidc/callback` and **Sign-out redirect address** `https://{workspace}.formalie.dev:2202/api/v1/auth/sso/signout`.
  - Google Workspace and SAML 2.0: **Reply (ACS) address** `https://{workspace}.formalie.dev:2202/api/v1/auth/sso/saml/acs`, **Entity ID (audience)** `https://{workspace}.formalie.dev:2202/api/v1/auth/sso/saml/metadata`, and **Formalie's metadata** (the same address; it downloads Formalie's SAML metadata).
- **Step 2, "From {provider}, paste these":** the values the provider gives you (Parts 3 to 5).
  - Microsoft Entra ID: **Issuer**, **Client ID**, **Client secret**.
  - Google Workspace and SAML 2.0: two tabs. **Metadata address** (best: certificates stay up to date by themselves; SAML 2.0 opens on it), or **Enter by hand** (Google Workspace opens on it): **Identity provider entity ID**, **Single sign-on address** (the provider may call it SSO URL or sign-on URL), **Signing certificate**.
- **Step 3, "Who signs in this way":**
  - **Button text:** what the sign-in page shows, "Continue with {text}" (for example `Microsoft` or `Okta`).
  - **Email domains:** the domain(s) of the provider's people (Parts 3 to 5 tell you which). A list of domains, not of people: nobody needs adding in advance. Only addresses of these domains (subdomains too) can sign in this way (anyone else is refused, FRM-AUTH-1014), and people typing such an address on the sign-in page are sent straight to the provider.
  - **Required for these domains:** leave **off** for the first test. On means those people can only sign in through the provider (their password stops working in this workspace).
  - **Create accounts on first sign-in:** **on** for this test (anyone the provider lets in gets an account). Off means only people already in People can sign in.
  - **Role for new accounts:** Member.

Then: **Save** → **Test** ("The test passed. You can turn it on.") → **Turn on**. The status reads "On", and the workspace's sign-in page shows "Continue with {text}".

The Test checks the provider's address and settings (it reads the OpenID configuration or the SAML metadata); the real proof is a sign-in (Part 7).

---
## Part 3. Microsoft Entra ID (OpenID Connect) → workspace `ssoentra`

**Account:** your Microsoft Entra tenant (the one you used for Azure). Open the **Microsoft Entra admin center**, entra.microsoft.com.

1. ⬜ **People.** **Identity → Users → All users → New user → Create new user**: User principal name `jane@{yourtenant}.onmicrosoft.com`, display name, a password (Microsoft asks them to change it at their first sign-in). Add two or three.
2. ⬜ **The app.** **Identity → Applications → App registrations → New registration**:
   - Name `Formalie`.
   - Supported account types: **Accounts in this organizational directory only (Single tenant)**.
   - Redirect URI: platform **Web**, paste Formalie's *Sign-in redirect address*.
   - Register.
3. ⬜ On the app's **Overview** copy **Application (client) ID** and **Directory (tenant) ID**.
4. ⬜ **Certificates & secrets → Client secrets → New client secret** → Add. Copy the **Value** column straight away (it is shown once). **Not** the "Secret ID": that was the mix-up on 2026-10-12 with the old Microsoft button (error AADSTS7000215 means the secret is wrong).
5. ⬜ **Token configuration → Add optional claim → ID** → tick `email`, `family_name`, `given_name` → Add (accept "Turn on the Microsoft Graph email permission"). Without it Formalie uses the sign-in name (`jane@…onmicrosoft.com`), which also works.
6. ⬜ **Authentication** → under Web, add Formalie's *Sign-out redirect address* as "Front-channel logout URL" (optional).
7. ⬜ **Formalie**, choice **Microsoft Entra ID**:
   - Issuer: `https://login.microsoftonline.com/{Directory (tenant) ID}/v2.0`.
   - Client ID: the Application (client) ID. Client secret: the Value from step 4.
   - Button text `Microsoft`, Email domains `{yourtenant}.onmicrosoft.com` (plus your own domain if you added one to Entra).
   - Save, Test, Turn on.

If your tenant has "security defaults" on, Microsoft may ask the test people to set up the Authenticator app at their first sign-in. That's Microsoft's side; finish it once.

## Part 4. Google Workspace (SAML) → workspace `ssogoogle`

**Account:** a **Google Workspace** subscription with an admin (a normal Gmail account can't do this). The Business Starter 14-day free trial at workspace.google.com is enough; it needs a domain you own. Then open admin.google.com.

1. ⬜ **People.** **Directory → Users → Add new user**: two or three people on your Workspace domain (for example `jane@yourcompany.com`).
2. ⬜ **The app.** **Apps → Web and mobile apps → Add app → Add custom SAML app**. App name `Formalie` → Continue.
3. ⬜ **Google Identity Provider details:** copy **SSO URL**, **Entity ID** and **Certificate** (or Download metadata and open it). Google gives no metadata *address*, so in Formalie you'll enter these by hand. Continue. To see them again later: **Apps → Web and mobile apps → Formalie → Download metadata**.
4. ⬜ **Service provider details:**
   - **ACS URL:** Formalie's *Reply (ACS) address*.
   - **Entity ID:** Formalie's *Entity ID (audience)*.
   - Start URL: empty. Signed response: leave off.
   - **Name ID format:** EMAIL. **Name ID:** Basic Information > Primary email.
   - Continue.
5. ⬜ **Attribute mapping:** Primary first name → `firstName`; Last name → `lastName`. Finish.
6. ⬜ **Turn it on for people:** open the app → **User access** → **ON for everyone** → Save. Google can take a few minutes (rarely longer) before it works; the error "app_not_configured_for_user" means wait or check this step.
7. ⬜ **Formalie**, choice **Google Workspace**:
   - On the **Enter by hand** tab (already open for Google Workspace): Identity provider entity ID = Google's Entity ID; Single sign-on address = Google's SSO URL; Signing certificate = Google's certificate, including the `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----` lines.
   - Button text `Google Workspace`, Email domains `yourcompany.com`.
   - Save, Test, Turn on.

## Part 5. SAML 2.0 (Okta, OneLogin and any other provider) → workspace `ssosaml`

Every provider other than Microsoft and Google signs people in through **SAML 2.0**: Okta, OneLogin, JumpCloud, PingOne, ADFS, Auth0, Keycloak and the rest. The Formalie side is always the same (Part 2, choice **SAML 2.0**); only the provider's screens differ. A workspace has one connection at a time, so test them one after another in `ssosaml` (change the values, Save, Test), or make a workspace for each.

### 5a. Mock SAML (quickest, no account)

Mock SAML (mocksaml.com) is a free public test provider. It is for testing only: it lets anyone in, never use it for real people.

1. ⬜ Open mocksaml.com and copy its **metadata address** shown there (at the time of writing `https://mocksaml.com/api/saml/metadata`). Mock SAML takes Formalie's ACS address and entity ID from the sign-in request itself, so nothing needs pasting on its side.
2. ⬜ **Formalie**, choice **SAML 2.0**:
   - Metadata address: Mock SAML's metadata address.
   - Button text `Company sign-in`, Email domains `example.com` (Mock SAML's people are `…@example.com`).
   - Save, Test, Turn on.
3. ⬜ At sign-in Mock SAML shows its own page: type any name `@example.com` (for example `jane@example.com`) and any password.

### 5b. Okta

**Account:** sign up for the free **Okta Integrator Free Plan** at developer.okta.com/signup. You get an address like `https://integrator-1234567.okta.com` and its Admin Console (`…-admin.okta.com`).

1. ⬜ **People first.** Admin Console → **Directory → People → Add person**: first name, last name, **Username and Primary email** in a made-up domain such as `jane@northwind-okta.test`; Password: "Set by admin", type one, untick "User must change password on first login". Save. Add two or three people.
2. ⬜ **The app.** **Applications → Applications → Create App Integration** → **SAML 2.0** → Next. App name `Formalie` → Next.
3. ⬜ **Configure SAML:**
   - **Single sign-on URL:** Formalie's *Reply (ACS) address* (leave "Use this for Recipient URL and Destination URL" ticked).
   - **Audience URI (SP Entity ID):** Formalie's *Entity ID (audience)*.
   - **Name ID format:** EmailAddress. **Application username:** Email.
   - **Attribute Statements:** `email` → `user.email`, `firstName` → `user.firstName`, `lastName` → `user.lastName`.
   - Next → "I'm an Okta customer adding an internal app" → Finish.
4. ⬜ On the app's **Sign On** tab, copy the **Metadata URL**.
5. ⬜ **Assignments** tab → **Assign → Assign to People** → assign your test people → Done.
6. ⬜ **Formalie**, choice **SAML 2.0**:
   - Metadata address: Okta's Metadata URL from step 4.
   - Button text `Okta`, Email domains `northwind-okta.test`.
   - Save, Test, Turn on.

### 5c. OneLogin

**Account:** a free developer account at onelogin.com/developer-signup (you get `https://{yourname}-dev.onelogin.com`).

1. ⬜ **People.** **Users → New User**: first name, last name, email in a made-up domain such as `jane@northwind-onelogin.test` → Save. Then **More Actions → Change Password** to give them a password.
2. ⬜ **The app.** **Applications → Applications → Add App** → search **SAML Custom Connector (Advanced)** → Display name `Formalie` → Save.
3. ⬜ **Configuration** tab:
   - **Audience (EntityID):** Formalie's *Entity ID (audience)*.
   - **Recipient:** Formalie's *Reply (ACS) address*.
   - **ACS (Consumer) URL Validator:** the ACS address as a pattern, dots and slashes escaped, for example `^https:\/\/ssosaml\.formalie\.dev:2202\/api\/v1\/auth\/sso\/saml\/acs$`.
   - **ACS (Consumer) URL:** Formalie's *Reply (ACS) address*.
   - **SAML initiator:** Service Provider. **SAML nameID format:** Email. **SAML signature element:** Assertion.
   - Save.
4. ⬜ **Parameters** tab → Add parameter `firstName` (value: First Name, tick "Include in SAML assertion"), and `lastName` (Last Name). Save.
5. ⬜ **SSO** tab: copy the **Issuer URL** (it looks like `https://app.onelogin.com/saml/metadata/…`). That is the metadata address.
6. ⬜ **Give people the app:** each user → **Applications** tab → **+** → Formalie → Continue → Save.
7. ⬜ **Formalie**, choice **SAML 2.0**:
   - Metadata address: the Issuer URL from step 5.
   - Button text `OneLogin`, Email domains `northwind-onelogin.test`.
   - Save, Test, Turn on.

### 5d. Any other provider

JumpCloud, PingOne, ADFS, Auth0, Keycloak and the rest: create a SAML 2.0 app there, give it Formalie's *Reply (ACS) address* and *Entity ID*, Name ID format **Email**, attributes `email`, `firstName`, `lastName` (Formalie also understands `givenName`, `surname`, `mail` and the Microsoft claim names), then paste its metadata address (or entity ID, sign-on address and certificate) into Formalie.

---

## Part 6. Production differences

- The addresses have no port and use `.com`: `https://{workspace}.formalie.com/api/v1/auth/sso/…` (the Cloudflare Worker passes them to the API, DEPLOYMENT-GUIDE). Formalie's screen always shows the right ones; customers copy from there.
- Customers do Parts 2 to 5 themselves with their real provider. Their workspace needs a plan with single sign-on (B15: paid in the portal; until then the platform admin sets it).
- `SAML_SP_CERT` / `SAML_SP_KEY` (PRODUCTION-CHECKLIST section 2) sign Formalie's SAML requests in production; some providers (ADFS, some PingFederate set-ups) require signed requests.

## Part 7. How the people sign in (the real test)

For each workspace, in a **private window** (so your own session doesn't get in the way):

1. ⬜ Open `https://{workspace}.formalie.dev:2202/auth/login`. You see the workspace's sign-in page with **Continue with {text}** next to email and password, Google and Facebook.
2. ⬜ **By the button:** press **Continue with {text}** → the provider's page → sign in as a test person → back in Formalie, signed in, on the dashboard.
3. ⬜ **By email:** sign out, type a test person's email (in the SSO domain) into the email field and continue: Formalie sends them straight to the provider.
4. ⬜ **In the owner's window:** **People** lists the new person with the role Member; **Audit trail** shows their sign-in through single sign-on.
5. ⬜ **Required:** in Settings → Sign-in → Single sign-on, turn on **Required for these domains** (Formalie warns if your own address is in the domain). In the private window, that person's password sign-in is now refused; only the provider works.
6. ⬜ **Turn off:** Turn off → the button disappears from the sign-in page; accounts stay.
7. ⬜ **Someone not allowed:** in the provider, remove a person's access to the app (Entra: Enterprise applications → Formalie → Properties → Assignment required on, then leave them out of Users and groups; Google: user access off; Okta: unassign; OneLogin: remove the app), then try: the provider itself refuses them, Formalie never signs them in.

## Part 8. When something goes wrong

| What you see | Usually means | Fix |
| --- | --- | --- |
| Provider: "redirect_uri mismatch" / "The redirect URI … does not match" | the address in the provider differs from Formalie's | copy Formalie's *Sign-in redirect address* again, exactly (port `:2202` included in development) |
| Microsoft AADSTS700016 | wrong Client ID | use the Application (client) ID |
| Microsoft AADSTS7000215 | wrong secret | use the secret's **Value**, not its Secret ID |
| Formalie: "The provider reports a different issuer" | the issuer has a missing / extra `/` or the wrong path | copy it as Microsoft writes it, ending with `/v2.0` |
| Formalie: "That address doesn't return SAML metadata" | a page address instead of the metadata address | Okta: the Sign On tab's Metadata URL; OneLogin: the SSO tab's Issuer URL; Google: use the Enter by hand tab |
| Formalie: "didn't share a verified email address" (FRM-AUTH-1021) | the provider sent no email, or an unverified one | Entra: add the `email` optional claim; SAML: Name ID format Email |
| Formalie: "Single sign-on didn't finish" (FRM-AUTH-1023) | the secret is wrong, the certificate changed, or the computer's clock is off by minutes | check the secret / certificate, run Test again, check the Windows clock |
| Google: "app_not_configured_for_user" | the app isn't on for that person yet | User access → ON, wait a few minutes |
| OneLogin: no redirect back | the ACS URL Validator pattern doesn't match | escape every `.` and `/` as in Part 5c |
| Can't get back in as owner | "Required" is on for your own domain | sign in through the provider, or ask Claude to turn it off in the development database |

Logs while testing: `powershell -ExecutionPolicy Bypass -File scripts\dev-logs.ps1` in formlyBackend shows each sign-in attempt and why it was refused (secrets and tokens are never written to the logs).
