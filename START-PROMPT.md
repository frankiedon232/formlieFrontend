# Start Prompt, formlyBackend

Open Claude Code in the `formlyBackend` root and paste everything inside the box below as your first message.

```
We are building the Formalie API backend (formlyBackend). The frontend
(C:\UNETPROJECTS\formalieFrontend) is finished and runs against a mock API;
this backend replaces that mock. Before doing anything:

1. Read CLAUDE.md in this root, then everything in docs/: 00-OVERVIEW.md,
   01-ARCHITECTURE.md, 02-DEV-ENVIRONMENT.md, 03-DECISIONS-AND-NOTES.md,
   SECURITY-PROTOCOL.md, API-CONTRACT.md, ERROR-CODES.md, OPTION-LISTS.md,
   BACKEND-SPEC.md, DATABASE-DESIGN.md, FRONTEND-REFERENCE.md,
   ENDPOINTS.md, PLATFORM-ADMIN-INTEGRATION.md, BACKEND-ROADMAP.md.
2. Look at the frontend (read only, never change it): shared/ (types and
   the rules to port), server/mock/ (the reference implementation) and
   test/. FRONTEND-REFERENCE.md says what to look for.
3. Inspect this project (app/ folder, the fmly venv, installed packages,
   the uvicorn entry point app.run:app) so you know exactly what exists.
4. Summarise back to me in a few lines: what you understood, anything
   unclear or conflicting, and your plan for Phase B0.

Do not write any code until I confirm the plan. Then work through
BACKEND-ROADMAP.md one phase at a time, ticking items and ENDPOINTS.md
boxes as you finish, and stop at the end of each phase for my review.
Any change to the API must be written back into docs/API-CONTRACT.md.
```

## Continuing in a new session

```
Read CLAUDE.md and docs/BACKEND-ROADMAP.md. Tell me which phase we are on
and what is left in it, then continue from there.
```
