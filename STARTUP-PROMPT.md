# Startup prompt (front end)

Open Claude Code in `C:\UNETPROJECTS\formaliePlatformFront` and add `C:\UNETPROJECTS\formalieFrontend` to the session as an extra folder (the foundation is copied from there). Then paste:

```
This is formaliePlatformFront, the Nuxt front end of the Formalie Platform Admin. It is a separate project from the Formalie portal; its backend is the separate project formaliePlatformBack. The whole plan is in this folder.

1. Read README.md, CLAUDE.md, PROGRESS.md and every file in docs/ (including docs/design/README.md and its images) before doing anything. docs/brand/ is the Formalie brand kit (logo, icons, favicon, manifest, OG image; rules in docs/brand/BRAND.md): use only these files for the logo and icons, never draw or invent one. The CLAUDE.md "Brand" section says where each file goes.
2. The Formalie portal's source is at C:\UNETPROJECTS\formalieFrontend. Read it only, never change it. This project copies its foundation from there (docs/FRONTEND-SPEC.md, first paragraph).
3. Set up git for this folder: create the repository with a main branch and a .gitignore (node_modules, .nuxt, .output, .env). Ask me for the remote URL before pushing.
4. Start phase P0 (Foundation) in PROGRESS.md: the Nuxt project in this folder, on its mock layer, at https://platformadm.formalie.dev:2203. Same stack as Formalie, no deviation, no Docker. Ask me before adding any dependency not listed in CLAUDE.md.
5. Before you start, tell me your P0 plan in short steps and list anything you need from me (hosts file line, certificate, remote URL). Wait for my go before building.

Keep PROGRESS.md and the docs in sync as you go, commit after every verified milestone, and stop for my review at the end of each phase.
```
