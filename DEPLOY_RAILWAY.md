# PC2 — Railway Deployment Guide

## Architecture on Railway

```
Railway Project: PC2
├── Service: pc2-backend (Python FastAPI)
│   ├── Dockerfile.railway
│   └── Root: /backend
├── Service: pc2-frontend (React, served by `serve`)
│   ├── Dockerfile.railway
│   └── Root: /frontend
├── Plugin: PostgreSQL (managed)
│   └── Auto-provisioned with DATABASE_URL
└── Plugin: Redis (managed)
    └── Auto-provisioned with REDIS_URL
```

## Step-by-Step Deployment

### 1. Create Railway Project

1. Go to https://railway.com/dashboard
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Connect `github.com/abhijain2903/pc2-railway`

### 2. Add Database Plugins

In the Railway project dashboard:

1. Click **+ New** → **Database** → **PostgreSQL**
   - This auto-creates `DATABASE_URL` env var
2. Click **+ New** → **Database** → **Redis**
   - This auto-creates `REDIS_URL` env var

### 3. Deploy Backend Service

1. Click **+ New** → **GitHub Repo** → select `pc2-railway`
2. In service settings:
   - **Root Directory:** `backend`
   - **Build Command:** (auto-detected from Dockerfile.railway)
3. Add environment variables:

```
DATABASE_URL          = (auto from PostgreSQL plugin — copy the connection string)
REDIS_URL             = (auto from Redis plugin)
OPENAI_API_KEY        = sk-proj-...your-key...
OPENAI_MODEL          = gpt-4o
DEMO_MODE             = false
SECRET_KEY            = (generate: openssl rand -hex 32)
CORS_ORIGINS          = https://your-frontend.up.railway.app,https://*.up.railway.app
```

4. Click **Deploy**

### 4. Run Database Migrations

Once backend is deployed, open **Railway CLI** or use the Railway shell:

```bash
# In Railway shell for the backend service:
# Option 1: Use Railway CLI
railway run --service pc2-backend bash

# Then run migrations against the Railway PostgreSQL:
for f in /app/supabase/migrations/*.sql; do
  psql $DATABASE_URL < "$f"
done
psql $DATABASE_URL < /app/supabase/seed.sql
```

Or run from local machine pointing to Railway DB:

```bash
# Get DATABASE_URL from Railway dashboard
export DATABASE_URL="postgresql://..."

for f in supabase/migrations/*.sql; do
  psql $DATABASE_URL < "$f"
done
psql $DATABASE_URL < supabase/seed.sql
```

### 5. Deploy Frontend Service

1. Click **+ New** → **GitHub Repo** → select `pc2-railway` again
2. In service settings:
   - **Root Directory:** `frontend`
   - **Build Command:** (auto-detected from Dockerfile.railway)
3. Add environment variable:

```
VITE_API_URL = https://your-backend-service.up.railway.app
```

(Get the backend URL from the backend service's Settings → Networking → Public URL)

4. Click **Deploy**

### 6. Generate Public URLs

For both services:
1. Go to service **Settings** → **Networking**
2. Click **Generate Domain** to get a `*.up.railway.app` URL

### 7. Update CORS

Once you have the frontend URL, update the backend's `CORS_ORIGINS`:

```
CORS_ORIGINS = https://pc2-frontend-production.up.railway.app
```

## Environment Variables Summary

### Backend Service

| Variable | Value | Required |
|---|---|---|
| `DATABASE_URL` | Auto from PostgreSQL plugin | Yes |
| `REDIS_URL` | Auto from Redis plugin | Yes |
| `OPENAI_API_KEY` | Your OpenAI key | Yes |
| `OPENAI_MODEL` | `gpt-4o` | No (default) |
| `ANTHROPIC_API_KEY` | Your Anthropic key | No |
| `SERPAPI_KEY` | Your SerpAPI key | No |
| `DEMO_MODE` | `false` | Yes |
| `SECRET_KEY` | Random 64-char string | Yes |
| `CORS_ORIGINS` | Frontend Railway URL | Yes |
| `ATHENA_DQ_URL` | DQ API endpoint | No |
| `SITEONE_PIM_URL` | SiteOne PIM endpoint | No |

### Frontend Service

| Variable | Value | Required |
|---|---|---|
| `VITE_API_URL` | Backend Railway URL (e.g. `https://pc2-backend-production.up.railway.app`) | Yes |

## Post-Deployment

1. Open frontend URL in browser
2. Login: `admin@iksula.com` / `demo123`
3. Change password via Admin > Users
4. Add your clients via Admin > Client Management
5. Upload a client template CSV
6. Start processing products

## Cost Estimate

| Resource | Railway Cost |
|---|---|
| Backend (512MB, always on) | ~$5/mo |
| Frontend (256MB, always on) | ~$3/mo |
| PostgreSQL (1GB) | ~$5/mo |
| Redis (25MB) | ~$3/mo |
| **Total** | **~$16/mo** |

Railway free tier includes $5/mo credit.
