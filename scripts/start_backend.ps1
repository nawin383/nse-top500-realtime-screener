# Start backend in mock mode
$env:DATA_MODE="mock"
Write-Host "Starting backend on http://localhost:8000 (mock mode)"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
