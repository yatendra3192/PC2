#!/bin/bash
# PC2 v2.0 — Setup & Deployment Script
# Run this from the project root: ./setup.sh

set -e

echo "============================================"
echo "  PC2 v2.0 — Product Content Creator Setup"
echo "============================================"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: docker is required. Install from https://docker.com"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Error: node is required. Install from https://nodejs.org"; exit 1; }

# Step 1: Create .env if not exists
if [ ! -f .env ]; then
    echo "[1/7] Creating .env from .env.example..."
    cp .env.example .env
    echo "  → Edit .env with your API keys before running in production"
else
    echo "[1/7] .env already exists, skipping"
fi

# Step 2: Start database + redis
echo "[2/7] Starting PostgreSQL + Redis via Docker..."
docker-compose up -d db redis
echo "  → Waiting for database to be ready..."
sleep 5

# Step 3: Run database migrations
echo "[3/7] Running database migrations..."
for f in supabase/migrations/*.sql; do
    echo "  → Running $f"
    docker exec -i $(docker-compose ps -q db) psql -U postgres -d pc2 < "$f" 2>/dev/null || true
done

# Step 4: Load seed data
echo "[4/7] Loading demo seed data..."
docker exec -i $(docker-compose ps -q db) psql -U postgres -d pc2 < supabase/seed.sql 2>/dev/null || echo "  → Seed data may already exist (OK)"

# Step 5: Install backend dependencies
echo "[5/7] Installing backend dependencies..."
cd backend
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt -q
cd ..

# Step 6: Install frontend dependencies
echo "[6/7] Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..

echo "[7/7] Setup complete!"
echo ""
echo "============================================"
echo "  To start PC2:"
echo "============================================"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source .venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Terminal 3 (Celery - optional):"
echo "    cd backend && celery -A app.tasks worker --loglevel=info"
echo ""
echo "  Then open: http://localhost:5173"
echo "  Login: admin@iksula.com / demo123"
echo ""
echo "  API docs: http://localhost:8000/api/docs"
echo "============================================"
