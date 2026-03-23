# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Stage 2: Backend + serve frontend
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy built frontend into /app/static
COPY --from=frontend-build /app/dist ./static

# Verify the app can be imported at build time
RUN python -c "import app.config; print('Config OK')" || true

ENV PORT=8000
EXPOSE ${PORT}

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"
