FROM python:3.11.11-slim as backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .python-version runtime.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY config ./config
COPY .env.example .env

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Frontend build stage
FROM node:18-alpine as frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:alpine as frontend
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
