#!/bin/sh
set -e

echo "🚀 Starting production entrypoint..."

# Wait for postgres
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "✅ PostgreSQL is ready"

# Run migrations
echo "📦 Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Setup complete, starting application..."
exec "$@"
