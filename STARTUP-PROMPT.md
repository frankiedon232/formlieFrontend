# Startup prompt (backend)

Open Claude Code in `C:\UNETPROJECTS\formaliePlatformBack`. Then paste:

```
This is formaliePlatformBack, the FastAPI backend of the Formalie Platform Admin, with its own database. It is a separate project from Formalie; its front end is the separate project formaliePlatformFront. The whole plan is in this folder.

1. Read README.md, CLAUDE.md, PROGRESS.md and every file in docs/ before doing anything. docs/brand/ holds the Formalie logo images for emails (rules in docs/brand/BRAND.md, use in the CLAUDE.md "Brand" section): use only these, never another logo.
2. Set up git for this folder: create the repository with a main branch and a .gitignore (padm/, __pycache__/, .env, .pytest_cache/, .mypy_cache/, .ruff_cache/). Ask me for the remote URL before pushing.
3. Start phase P0 (Foundation) in PROGRESS.md: the FastAPI project in this folder (Python 3.11.9, venv padm) on https://platformapi.formalie.dev:5601. Same stack as Formalie's backend, no deviation, no Docker: use the services already installed on this machine (PostgreSQL, Redis, RabbitMQ, MinIO, Mailpit) as docs/02-DEV-ENVIRONMENT.md describes. Ask me before adding any library not listed in CLAUDE.md.
4. Never write to Formalie's database or call Formalie's system except the way docs/FORMALIE-INTEGRATION.md describes; until Formalie's backend provides what it lists, work against a fake Formalie in the tests.
5. Before you start, tell me your P0 plan in short steps and list anything you need from me (hosts file line, certificate, database login, RabbitMQ vhost and user, MinIO bucket, remote URL). Wait for my go before building.

Keep PROGRESS.md and the docs in sync as you go, commit after every verified milestone, and stop for my review at the end of each phase.
```
