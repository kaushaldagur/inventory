# Deployment guide (yourinventory)

Use this guide for **GitHub**, **Docker Hub**, **Render** (backend + Postgres), and **Vercel** (frontend).

Replace placeholders:

| Placeholder | Example |
|-------------|---------|
| `YOUR_GITHUB_USER` | `kaushaldagur` |
| `YOUR_DOCKERHUB_USER` | `kaushaldagur` |
| `YOUR_BACKEND_URL` | `https://inventory-api.onrender.com` |
| `YOUR_FRONTEND_URL` | `https://yourinventory.vercel.app` |

---

## Part 1 — GitHub repository

```bash
cd /Users/shivaniverma/Documents/inventory
git init
git add .
git commit -m "Inventory & order management system — yourinventory"
```

Create an empty repo on GitHub (no README), then:

```bash
git remote add origin https://github.com/YOUR_GITHUB_USER/inventory.git
git branch -M main
git push -u origin main
```

**Submission:** `https://github.com/YOUR_GITHUB_USER/inventory`

---

## Part 2 — Docker Hub backend image

### 2.1 Create Docker Hub account

1. Sign up at [https://hub.docker.com](https://hub.docker.com)
2. Create a repository: **inventory-backend** (public)

### 2.2 Log in and publish (on your Mac)

```bash
cd /Users/shivaniverma/Documents/inventory
docker login

# Build production image
docker build -t YOUR_DOCKERHUB_USER/inventory-backend:latest ./backend

# Optional version tag
docker tag YOUR_DOCKERHUB_USER/inventory-backend:latest YOUR_DOCKERHUB_USER/inventory-backend:1.0.0

# Push
docker push YOUR_DOCKERHUB_USER/inventory-backend:latest
docker push YOUR_DOCKERHUB_USER/inventory-backend:1.0.0
```

Or use the helper script:

```bash
sh scripts/publish-docker.sh YOUR_DOCKERHUB_USER
```

**Submission:** `https://hub.docker.com/r/YOUR_DOCKERHUB_USER/inventory-backend`

---

## Part 3 — PostgreSQL + backend (Render)

### 3.1 PostgreSQL on Render

1. [Render Dashboard](https://dashboard.render.com) → **New +** → **PostgreSQL**
2. Name: `inventory-db`, region near you, free tier if available
3. After create, copy **Internal Database URL** (for backend on Render) or **External** (for local tools)

### 3.2 Web service (Docker)

1. **New +** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Name:** `inventory-api`
   - **Root Directory:** `backend`
   - **Runtime:** **Docker**
   - **Instance type:** Free (if available)

4. **Environment variables:**

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Paste Render Postgres URL (postgres://… is OK) |
| `JWT_SECRET` | Long random string (e.g. `openssl rand -hex 32`) |
| `ENV` | `production` |
| `FRONTEND_ORIGIN` | Your Vercel URL (set after Part 4), e.g. `https://yourinventory.vercel.app` |

5. **Deploy** → wait until **Live**
6. Copy public URL, e.g. `https://inventory-api.onrender.com`
7. Test: `https://inventory-api.onrender.com/health` → `{"status":"ok"}`

### 3.3 Create login user on Render

Render → your web service → **Shell**:

```bash
python /app/scripts/create_user.py \
  --name "Kaushal Dagur" \
  --email "kaushal.dagur@inventory.com" \
  --password "kaushal123"
```

**Submission:** `https://inventory-api.onrender.com` (your real URL)

---

## Part 4 — Frontend (Vercel)

1. [Vercel](https://vercel.com) → **Add New** → **Project** → import GitHub repo
2. Settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

3. **Environment variable:**

| Key | Value |
|-----|--------|
| `VITE_API_URL` | `https://inventory-api.onrender.com` (your backend URL, no trailing slash) |

4. **Deploy** → copy URL, e.g. `https://yourinventory.vercel.app`

### 4.1 Connect frontend to backend (CORS)

Back on **Render** → backend service → **Environment**:

- Set `FRONTEND_ORIGIN` = `https://yourinventory.vercel.app` (exact Vercel URL, no trailing slash)
- **Save** → redeploy backend

### 4.2 Verify

1. Open Vercel URL → sign in with credentials from Part 3.3  
2. Add a product → should save without CORS errors  

**Submission:** `https://yourinventory.vercel.app` (your real URL)

---

## Part 5 — Submission checklist

| Item | Where to get it |
|------|------------------|
| GitHub repo | Part 1 |
| Docker Hub image | `https://hub.docker.com/r/YOUR_DOCKERHUB_USER/inventory-backend` |
| Live backend API | Render service URL + `/docs` |
| Live frontend | Vercel URL |

Example submission block:

```text
GitHub: https://github.com/YOUR_GITHUB_USER/inventory
Docker Hub: https://hub.docker.com/r/YOUR_DOCKERHUB_USER/inventory-backend
Frontend: https://yourinventory.vercel.app
Backend: https://inventory-api.onrender.com
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| CORS error in browser | `FRONTEND_ORIGIN` must match Vercel URL exactly; redeploy backend |
| Login fails | Run `create_user.py` on Render shell |
| `Invalid or expired token` | Clear browser storage; sign in again |
| Backend sleeps (free tier) | First request after idle may take ~30s |
| `DATABASE_URL` errors | Use full Postgres URL from Render; app auto-converts `postgres://` |

---

## Alternative: Railway

1. New project → **PostgreSQL** + **Web Service** from repo  
2. Web service: root `backend`, Dockerfile path `Dockerfile`  
3. Same env vars as Render (`DATABASE_URL`, `JWT_SECRET`, `ENV=production`, `FRONTEND_ORIGIN`)  
4. Railway sets `PORT` automatically (supported by entrypoint)
