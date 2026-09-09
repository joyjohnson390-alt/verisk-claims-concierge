#!/bin/bash
set -e

# Start mock APIs in background (internal only, not public)
python -m uvicorn mock_apis.weather_api:app --host 0.0.0.0 --port 8001 --log-level error &
python -m uvicorn mock_apis.acculynx_api:app --host 0.0.0.0 --port 8002 --log-level error &

# Initialize DB, seed data, and knowledge base
python -c "
from db.database import init_db; init_db()
from data.seed_data import seed; seed()
from knowledge_base.kb import init_kb; init_kb()
print('[startup] DB, seed data, and knowledge base ready.')
"

# Start main web app on Railway's dynamic PORT
exec uvicorn app.web:app --host 0.0.0.0 --port "${PORT:-8000}"
