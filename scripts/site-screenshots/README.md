# Website screenshots

These tools make the cropped, watermarked shots of the app that the website uses (`formalieSite/docs/screenshots/`), on sample data only. The owner set the rule on 2026-10-10: show only the part a section needs, for security.

1. Run the app's own dev server (`pnpm dev`, port 2202). Never start a second one.
2. Start headless Chrome with remote debugging on port 9333:
   ```bash
   "C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --remote-debugging-port=9333 --user-data-dir=.chrome-shots --ignore-certificate-errors --window-size=1440,900 about:blank
   ```
3. Sign it in with a seeded test account. It's the mock's local seed only; the password is read from the project and never printed:
   ```bash
   node scripts/site-screenshots/login.mjs <seeded admin email>
   ```
4. Take the shots (all of them, or the ids you list):
   ```bash
   OUT=formalieSite/docs/screenshots node scripts/site-screenshots/sitecap.mjs scripts/site-screenshots/plan.json [id …]
   ```

## What `plan.json` holds

- **`shots`:** `id`, `path` (the app page), `open` (`row` · `grid` · `table`), `target` (what to crop: `card:<title>`, `body:<height>`, `panel:<height>`, `dialog`, `rect:x,y,w,h`) and `mode` (`dark` for the dark versions).
- **`replace`:** sample text put in place of real keys, test names, people and the workspace name before each shot.

Uploaded logos and photos become an "N" monogram, the tour card is hidden, and the watermark ("Formalie · formalie.com") is baked into the pixels in light and dark. Take the sign-in shot last: it leaves the workspace session.
