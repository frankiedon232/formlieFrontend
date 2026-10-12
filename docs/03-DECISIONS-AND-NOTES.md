# Decisions and notes

- **The website and the app are separate projects** (owner 2026-10-10). The website is `formalieSite` (Nuxt, on port 3033 in development); the app is `formalieFrontend` (port 2202); the platform admin is `formaliePlatformFront` and `formaliePlatformBack`.
- **Addresses:** the website is at `https://formalie.dev:3033/` in development. The owner gave the same address for production; the expected production address is `https://formalie.com/`, so confirm it with the owner before launch.
- **The references are ideas, not targets** (owner): "this is just an idea, it does not cancel the screens of the app". The website follows the app's look.
- **Only the parts of the app that are needed are shown** (owner: "not all, for security"). Screens are cropped, watermarked and on sample data (`SECURITY.md`).
- **Light and dark screens are mixed** across the site (owner 2026-10-10).
- **The hero grows from the sign-in animation "in a different way"** (owner): the same idea (sources → hub → destinations), richer and larger, and the hub is **always Formalie** (owner: "my name can not diminish").
- **Legal pages look like documentation** (owner), with their text from the platform admin later; placeholders until then.
- **The links to the portal forms come later** (owner): contact, Enterprise and newsletter are Formalie's own forms, embedded, wired in phase S6.
- **No custom CSS anywhere** (owner, in the app): customers never write code, so the website doesn't promise it.
- **Prices are samples** until the owner sets them in the platform admin; the website reads them from the public plans endpoint.
