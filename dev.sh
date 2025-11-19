#!/bin/bash

# Wedding RSVP Backend - Local Development Startup
# Reads all configuration from .env file

set -e

echo "🚀 Wedding RSVP Backend - Local Development"
echo "============================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "Please create .env file:"
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

# Load environment variables from .env
export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

# Activate virtual environment (from .env)
if [ -n "$VENV_PATH" ] && [ -d "$VENV_PATH" ]; then
    echo "🐍 Activating virtual environment: $VENV_PATH"
    source "$VENV_PATH/bin/activate"
    echo "✅ Virtual environment activated"
else
    echo "⚠️  VENV_PATH not set or not found, using system Python"
fi
echo ""

# Start PostgreSQL with Docker
echo "🐘 Starting PostgreSQL with Docker..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 3

until docker exec wedding-postgres pg_isready -U wedding_user -d wedding_db > /dev/null 2>&1; do
    echo "   Still waiting for PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL is ready!"
echo ""

# Start the Flask application
PORT=${PORT:-5001}
echo "🌐 Starting Flask server on http://localhost:$PORT"
echo "📊 Database: $DATABASE_URL"
echo ""
echo "Press Ctrl+C to stop the server"
echo "To stop PostgreSQL: docker-compose down"
echo "============================================"
echo ""

python app.py
