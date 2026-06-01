# yourinventory — Inventory & Order Management System

Full-stack app for managing **products**, **customers**, **orders**, and **inventory tracking**.

- **Backend:** Python, FastAPI, PostgreSQL  
- **Frontend:** React (JavaScript)  
- **Infrastructure:** Docker, Docker Compose  

## Features

- **Login only** — accounts are created by an administrator (CLI), not via the UI  
- **Per-user data** — each login sees only their own products, customers, orders, and stock  
- Product / customer / order CRUD with assignment business rules  
- Dashboard with stats and charts  

## Business flow

1. **Administrator** creates login users (CLI).  
2. **User signs in** → receives a JWT token.  
3. **Products** → catalog + stock (SKU unique per user).  
4. **Customers** → buyers (email unique per user).  
5. **Orders** → stock check, auto total, stock reduction.  
6. **Dashboard** → totals, charts, low-stock alerts.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Create the first login user:

```bash
docker compose exec backend python /app/scripts/create_user.py \
  --name "Kaushal Dagur" \
  --email "kaushal.dagur@inventory.com" \
  --password "kaushal123"
```

| Service   | URL |
|-----------|-----|
| Frontend  | http://localhost:3000 |
| Backend   | http://localhost:8000 |
| API docs  | http://localhost:8000/docs |

Sign in at http://localhost:3000 with the email and password you created.

## Create additional users (backend only)

```bash
docker compose exec backend python /app/scripts/create_user.py \
  --name "Full Name" \
  --email "user@example.com" \
  --password "your-secure-password"
```

## Run tests

```bash
docker compose run --rm --no-deps --entrypoint sh \
  -v "$(pwd)/backend/tests:/app/tests" \
  backend -c 'pip install -q pytest httpx && export PATH=$HOME/.local/bin:$PATH && export DATABASE_URL=sqlite:////tmp/test.db && export JWT_SECRET=test && python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)" && pytest /app/tests -q'
```

API smoke test (create a user first, or set `TEST_USER_EMAIL` / `TEST_USER_PASSWORD` in `.env`):

```bash
sh scripts/test-api.sh
```

## API summary

| Area | Endpoints |
|------|-----------|
| Auth | `POST /auth/login`, `GET /auth/me` |
| Products | `POST/GET/GET{id}/PUT/DELETE /products` |
| Customers | `POST/GET/GET{id}/DELETE /customers` |
| Orders | `POST/GET/GET{id}/DELETE /orders` |
| Dashboard | `GET /dashboard` |

All inventory routes require `Authorization: Bearer <token>`.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Database credentials |
| `DATABASE_URL` | Backend DB connection (set automatically in Compose) |
| `JWT_SECRET` | **Required in production** — signing key for login tokens |
| `VITE_API_URL` | Public backend URL (frontend build) |
| `FRONTEND_ORIGIN` | CORS origin for deployed frontend |
| `ENV` | `production` disables `create_all`; migrations run on startup |

## Deployment checklist

**Step-by-step guide:** see [DEPLOYMENT.md](./DEPLOYMENT.md) (GitHub, Docker Hub, Render, Vercel).

### Backend (Render / Railway / Fly.io)

1. PostgreSQL database + `DATABASE_URL`  
2. `JWT_SECRET` — long random string  
3. `FRONTEND_ORIGIN` — e.g. `https://your-app.vercel.app`  
4. `ENV=production`  
5. Migrations run automatically via container entrypoint  

### Frontend (Vercel / Netlify)

1. Root: `frontend`  
2. `VITE_API_URL` — e.g. `https://your-api.onrender.com`  

### After deploy

1. Create users via shell on the backend host:

   ```bash
   python /app/scripts/create_user.py --name "..." --email "..." --password "..."
   ```

2. Push backend image to Docker Hub (submission):

   ```bash
   sh scripts/publish-docker.sh YOUR_DOCKERHUB_USER
   ```

   Link format: `https://hub.docker.com/r/YOUR_DOCKERHUB_USER/inventory-backend`

## Submission checklist

- [ ] GitHub repository link  
- [ ] Docker Hub backend image link  
- [ ] Live frontend URL  
- [ ] Live backend API URL  
