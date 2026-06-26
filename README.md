# AiNameProject

AI naming app with a uni-app frontend and a FastAPI backend.

## Project Structure

```text
AiNameProject/
  ainame/     Frontend uni-app project
  backend/    FastAPI backend
```

## Backend

Run backend commands from the `backend/` directory so the current import paths work correctly.

```powershell
cd backend
uvicorn main:app --reload
```

After startup, open:

```text
http://127.0.0.1:8000/
```

Expected response:

```json
{"message":"Hello World"}
```

## Frontend

Open `ainame/` with HBuilderX or another uni-app compatible tool and run the app from there.

The frontend request helper is in `ainame/http/http.js`. It calls the backend on port `8000` using the current host name in browser builds.

## Git Workflow

Use `main` as the stable branch. Build each module on a feature branch and merge it back with a pull request after review.

Recommended branch examples:

```text
feature/module-1-naming
feature/community-vote
feature/api-key
feature/invite-credits
```

Before starting new work, sync from `main`:

```powershell
git checkout main
git pull origin main
git checkout -b feature/your-module
```

## Current Module Split

This branch starts with structure cleanup, then module 1 work.

Our side:

- Module 1: naming core form/schema/prompt/result updates.
- Module 2: `.com` domain checks for generated names.
- Module 3: enterprise-only slogan and logo placeholder flow.
- Admin cleanup for user bans, roles, sensitive words, and logs.

Teammate side:

- Community voting.
- API Key page and generation API.
- Invitation credits.
