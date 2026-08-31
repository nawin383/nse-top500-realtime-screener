#!/usr/bin/env bash
set -e
echo "Python $(python --version) pip $(pip --version)"
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
echo "Backend deps OK"
if [ -d "frontend" ]; then
  echo "Building frontend..."
  cd frontend
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found, installing Node 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
  fi
  npm ci
  npm run build
  cd ..
  echo "Frontend built to frontend/dist"
  ls -lh frontend/dist/ | head -20
else
  echo "No frontend dir"
fi
