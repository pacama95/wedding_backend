# Local Development Guide

## Prerequisites

- ✅ Python 3.11+ with virtual environment
- ✅ Docker (for PostgreSQL)

## Setup (First Time)

```bash
# 1. Copy the environment file
cp .env.example .env

# 2. (Optional) Edit .env if needed
# Default settings work for local development

# 3. Install dependencies
source /Users/pacama95/venv/bin/activate
pip install -r requirements.txt
```

## Daily Development

### Start the API
```bash
./dev.sh
```

This single command will:
1. Load settings from `.env`
2. Activate your virtual environment
3. Start PostgreSQL in Docker
4. Start the Flask API on port 5001

### Test the API
In another terminal:
```bash
cd /Users/pacama95/Projects/wedding_web/backend
source /Users/pacama95/venv/bin/activate
python test_api.py
```

### Stop Everything
Press `Ctrl+C` in the server terminal, then:
```bash
docker-compose down
```

## Configuration

All settings are in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Docker PostgreSQL |
| `PORT` | API server port | 5001 |
| `VENV_PATH` | Python virtual environment | /Users/pacama95/venv |
| `GOOGLE_CREDENTIALS_JSON` | Google Sheets auth (optional) | - |
| `GOOGLE_SHEET_NAME` | Sheet name (optional) | Wedding Confirmations |

## Useful Commands

### View database
```bash
docker exec -it wedding-postgres psql -U wedding_user -d wedding_db
```

### View all guests
```bash
docker exec -it wedding-postgres psql -U wedding_user -d wedding_db \
  -c "SELECT nombre, apellidos, asistencia FROM guests;"
```

### Clear all data
```bash
docker exec -it wedding-postgres psql -U wedding_user -d wedding_db \
  -c "TRUNCATE TABLE guests RESTART IDENTITY;"
```

### Check PostgreSQL logs
```bash
docker-compose logs -f postgres
```

## Troubleshooting

### Port 5001 already in use
Edit `.env` and change `PORT=5001` to another port (e.g., `PORT=5002`)

### PostgreSQL won't start
```bash
docker-compose down -v
docker-compose up -d
```

### Module not found errors
```bash
source /Users/pacama95/venv/bin/activate
pip install -r requirements.txt
```

### Can't connect to database
Make sure PostgreSQL is running:
```bash
docker ps | grep wedding-postgres
```

## Files Overview

- `dev.sh` - Main startup script (reads from .env)
- `.env` - Local configuration (not in git)
- `.env.example` - Template for .env
- `docker-compose.yml` - PostgreSQL configuration
- `app.py` - Flask application
- `test_api.py` - API test suite
- `requirements.txt` - Python dependencies
