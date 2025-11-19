# Wedding RSVP Backend

Python Flask backend for managing wedding guest confirmations with PostgreSQL storage and Google Sheets synchronization.

## 🚀 Quick Start (Local Development)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Update .env with your settings (already configured for local dev)

# 3. Start everything (PostgreSQL + API)
./dev.sh

# 4. Test the API (in another terminal)
python test_api.py
```

That's it! The API will be running at `http://localhost:5001`

## Features

- ✅ **Smart Guest Validation**: Prevents duplicate guest registrations with intelligent name matching
  - Case-insensitive comparison (Juan = JUAN = juan)
  - Accent-insensitive comparison (José = Jose, María = Maria)
  - Handles Spanish characters (ñ, á, é, í, ó, ú)
- 💾 **PostgreSQL Storage**: Persistent database storage
- 📊 **Google Sheets Sync**: Automatic synchronization to Google Sheets
- 🚀 **Railway Ready**: Configured for Railway deployment

## API Endpoints

### POST `/api/guests`
Create a new guest RSVP

**Request Body:**
```json
{
  "nombre": "Juan",
  "apellidos": "Pérez García",
  "asistencia": "si",
  "acompanado": "si",
  "adultos": 2,
  "ninos": 1,
  "autobus": "ida_y_vuelta",
  "alergias": "Ninguna",
  "comentarios": "¡Muy emocionados!"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "¡Confirmación recibida con éxito!",
  "guest": {
    "id": 1,
    "nombre": "Juan",
    "apellidos": "Pérez García",
    "created_at": "2024-01-15T10:30:00"
  },
  "synced_to_sheets": true
}
```

**Error Response (409) - Duplicate:**
```json
{
  "error": "Este nombre ya ha sido registrado..."
}
```

### GET `/api/guests`
Get all guests (admin endpoint)

### GET `/health`
Health check endpoint

## 📝 Configuration (.env file)

All local settings are configured in the `.env` file:

```bash
# Database (Docker PostgreSQL)
DATABASE_URL=postgresql://wedding_user:wedding_pass@localhost:5432/wedding_db

# Server port
PORT=5001

# Virtual environment path (for dev.sh)
VENV_PATH=/Users/pacama95/venv

# Optional: Google Sheets sync via Apps Script
# GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
```

## 🛑 Stop the Server

Press `Ctrl+C` to stop Flask, then:
```bash
docker-compose down
```

## Railway Deployment

### 1. Create Railway Project
1. Go to [Railway](https://railway.app)
2. Create a new project
3. Select "Deploy from GitHub repo"
4. Connect your repository

### 2. Configure Root Directory
Railway needs to know to deploy from the `backend` folder:

**Option A: Using Railway Dashboard (Recommended)**
1. Go to your Railway project settings
2. Under "Service Settings" → "Root Directory"
3. Set to: `backend`

**Option B: Using Configuration Files**
The repository includes `railway.toml` and `nixpacks.toml` at the root that configure Railway to use the backend directory.

### 3. Add PostgreSQL Database
1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically set the `DATABASE_URL` environment variable

### 4. Configure Environment Variables
In Railway project settings, add:

- `DATABASE_URL` - (automatically set by Railway PostgreSQL)
- `GOOGLE_APPS_SCRIPT_URL` - Your Google Apps Script URL (optional)

### 5. Deploy
Railway will automatically deploy your application when you push to your repository.

**Verify Deployment:**
- Check that Railway is using Python (not serving static HTML)
- Test the health endpoint: `https://your-app.railway.app/health`
- Should return: `{"status": "healthy"}`

## Google Sheets Setup

The backend uses your existing Google Apps Script to sync data to Google Sheets.

### 1. Get Your Apps Script URL

If you already have a Google Apps Script set up:
1. Open your Google Sheet
2. Go to **Extensions** → **Apps Script**
3. Click **Deploy** → **Manage deployments**
4. Copy the **Web app URL**

If you need to create one, see `google-sheets-integration.md` for detailed instructions.

### 2. Add to Environment Variables

**Local (.env file):**
```bash
GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
```

**Railway:**
Add `GOOGLE_APPS_SCRIPT_URL` as an environment variable in your Railway project settings.

## Database Schema

```sql
CREATE TABLE guests (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    apellidos VARCHAR(255) NOT NULL,
    nombre_normalized VARCHAR(255) NOT NULL,
    apellidos_normalized VARCHAR(255) NOT NULL,
    asistencia VARCHAR(50) NOT NULL,
    acompanado VARCHAR(10) NOT NULL,
    adultos INTEGER DEFAULT 0,
    ninos INTEGER DEFAULT 0,
    autobus VARCHAR(50),
    alergias TEXT,
    comentarios TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nombre_normalized, apellidos_normalized)
);
```

**Note:** The `nombre` and `apellidos` fields store the original names as entered by the user (e.g., "José García"). The `nombre_normalized` and `apellidos_normalized` fields store the lowercase, accent-free versions (e.g., "jose garcia") for uniqueness checking.

## Google Sheets Format

The sheet should have these columns:
| Date | Name | Attendance | With Companions | Adults | Children | Bus | Allergies | Comments |
|------|------|------------|-----------------|--------|----------|-----|-----------|----------|

## Testing

### Test with curl
```bash
# Create a guest
curl -X POST http://localhost:5000/api/guests \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Test",
    "apellidos": "User",
    "asistencia": "si",
    "acompanado": "no",
    "adultos": 0,
    "ninos": 0,
    "autobus": "no"
  }'

# Get all guests
curl http://localhost:5000/api/guests

# Health check
curl http://localhost:5000/health
```

## Security Notes

- The backend validates all incoming data
- Duplicate names are prevented by storing normalized versions (lowercase, no accents)
- Database has UNIQUE constraint on `(nombre_normalized, apellidos_normalized)`
- Original names are preserved for display purposes
- CORS is enabled for frontend integration
- Google Sheets sync is non-blocking (won't fail the request if it fails)

## Name Normalization

The system uses intelligent name matching to prevent duplicates:

**Examples of detected duplicates:**
- "José García" = "Jose Garcia" = "JOSE GARCIA" = "josé garcía"
- "María López" = "Maria Lopez" = "MARÍA LÓPEZ"
- "Ángel Pérez" = "Angel Perez" = "angel perez"

**How it works:**
1. When a guest registers, their name is stored in **two formats**:
   - **Original**: "José García" (preserved for display)
   - **Normalized**: "jose garcia" (lowercase, no accents, for comparison)
2. The database has a UNIQUE constraint on the normalized fields
3. All comparisons use the simple normalized version

**Benefits:**
- ✅ Simple and fast comparisons (no complex SQL functions)
- ✅ Original names preserved for display and Google Sheets
- ✅ Database-level uniqueness enforcement
- ✅ No dependencies on PostgreSQL extensions

This ensures that guests can't accidentally register twice with slight variations in capitalization or accent marks.

## Troubleshooting

**Database connection errors:**
- Verify `DATABASE_URL` is correctly set
- Check if PostgreSQL is running (local) or accessible (Railway)

**Google Sheets not syncing:**
- Verify `GOOGLE_CREDENTIALS_JSON` is valid JSON
- Check if the service account has access to the sheet
- Look at application logs for specific errors

**CORS errors:**
- Make sure the frontend URL is allowed (CORS is currently set to allow all origins)
- Update CORS configuration in `app.py` if needed

## License

MIT
