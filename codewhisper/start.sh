#!/bin/bash
set -e

echo "=== CodeWhisper Starting ==="
echo "Working dir: $(pwd)"
echo "FLASK_ENV: $FLASK_ENV"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo yes || echo no)"

# Run database migrations
echo "Running DB migrations..."
flask db upgrade || python3 -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created via create_all()')
"

# Seed problem bank if empty
echo "Checking problem bank..."
python3 -c "
from app import create_app
from app.models.problem import Problem
import sys, os
app = create_app()
with app.app_context():
    count = Problem.query.count()
    if count == 0:
        sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
        from scripts.seed_problems import seed
        n = seed(verbose=False, app=app)
        print(f'Seeded {n} problems')
    else:
        print(f'Problem bank has {count} problems - skipping seed')
" || echo "Seed skipped (non-fatal)"

# Start gunicorn
echo "Starting gunicorn..."
exec gunicorn run:app \
    --bind "0.0.0.0:${PORT:-5000}" \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
