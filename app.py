import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import unicodedata
import logging
import json as json_lib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wedding_api.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
_db_initialized = False

# Google Sheets configuration
GOOGLE_APPS_SCRIPT_URL = os.environ.get('GOOGLE_APPS_SCRIPT_URL')

def normalize_name(name):
    """
    Normalize a name for comparison by:
    - Converting to lowercase
    - Removing accents/diacritics (tildes)
    - Stripping whitespace
    """
    # Remove accents using unicode normalization
    # NFD = Canonical Decomposition, then filter out combining characters
    nfd = unicodedata.normalize('NFD', name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    # Convert to lowercase and strip whitespace
    return without_accents.lower().strip()

def get_db_connection():
    """Create a database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Initialize the database with the guests table"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS guests (
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
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def ensure_database_initialized():
    """Ensure the database schema exists (idempotent)."""
    global _db_initialized
    if _db_initialized:
        return

    if not DATABASE_URL:
        logger.warning("⚠️  DATABASE_URL not set - database will not be initialized")
        return

    logger.info("Initializing database (ensure)...")
    try:
        init_db()
        _db_initialized = True
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {str(e)}", exc_info=True)

def add_to_google_sheets_via_script(guest_data):
    """Add guest data to Google Sheets via Google Apps Script"""
    import requests
    from urllib.parse import urlencode
    
    if not GOOGLE_APPS_SCRIPT_URL:
        logger.warning("Google Apps Script URL not configured - skipping sheets sync")
        return False
    
    try:
        # Prepare data in the same format as the frontend was sending
        full_name = f"{guest_data['nombre']} {guest_data['apellidos']}"
        params = {
            'nombre': full_name,
            'asistencia': guest_data['asistencia'],
            'acompanado': guest_data['acompanado'],
            'adultos': guest_data['adultos'],
            'ninos': guest_data['ninos'],
            'autobus': guest_data['autobus'],
            'alergias': guest_data['alergias'],
            'comentarios': guest_data['comentarios']
        }
        
        logger.info(f"Syncing to Google Sheets - Guest: {full_name}")
        logger.debug(f"Google Sheets params: {params}")
        
        # Send to Google Apps Script (same as frontend was doing)
        response = requests.post(GOOGLE_APPS_SCRIPT_URL, data=params, timeout=10)
        
        logger.info(f"Google Sheets response - Status: {response.status_code}, Body: {response.text[:200]}")
        
        if response.status_code == 200:
            logger.info(f"✓ Successfully synced to Google Sheets: {full_name}")
            return True
        else:
            logger.error(f"✗ Error syncing to Google Sheets - Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Exception adding to Google Sheets: {str(e)}", exc_info=True)
        return False

def add_to_google_sheets(guest_data):
    """Add guest data to Google Sheets via Google Apps Script"""
    return add_to_google_sheets_via_script(guest_data)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@app.before_first_request
def initialize_database_on_first_request():
    ensure_database_initialized()

@app.route('/api/guests', methods=['POST'])
def create_guest():
    """
    Create a new guest RSVP
    Validates uniqueness, stores in PostgreSQL, and syncs to Google Sheets
    """
    request_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    logger.info(f"[{request_id}] ========== NEW GUEST REQUEST ==========")
    logger.info(f"[{request_id}] Method: {request.method}, Path: {request.path}")
    logger.info(f"[{request_id}] Remote Address: {request.remote_addr}")
    logger.info(f"[{request_id}] User Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        logger.info(f"[{request_id}] Request Data: {json_lib.dumps(data, ensure_ascii=False)}")
        
        # Validate required fields
        required_fields = ['nombre', 'apellidos', 'asistencia', 'acompanado']
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"[{request_id}] ✗ Validation failed - Missing field: {field}")
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Prepare guest data
        guest_data = {
            'nombre': data['nombre'].strip(),
            'apellidos': data['apellidos'].strip(),
            'asistencia': data['asistencia'],
            'acompanado': data['acompanado'],
            'adultos': int(data.get('adultos', 0)),
            'ninos': int(data.get('ninos', 0)),
            'autobus': data.get('autobus', 'no'),
            'alergias': data.get('alergias', ''),
            'comentarios': data.get('comentarios', '')
        }
        
        # Normalize names for storage and comparison
        first_name_normalized = normalize_name(guest_data['nombre'])
        last_names_normalized = normalize_name(guest_data['apellidos'])
        
        logger.info(f"[{request_id}] Guest: {guest_data['nombre']} {guest_data['apellidos']}")
        logger.info(f"[{request_id}] Normalized: {first_name_normalized} {last_names_normalized}")
        logger.info(f"[{request_id}] Attendance: {guest_data['asistencia']}, Companions: {guest_data['acompanado']}")
        
        # Connect to database
        logger.debug(f"[{request_id}] Connecting to database...")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if guest already exists with multiple strategies
        logger.debug(f"[{request_id}] Checking for duplicate...")
        
        # Strategy 1: Exact match on normalized names
        cur.execute('''
            SELECT id, nombre, apellidos 
            FROM guests 
            WHERE nombre_normalized = %s AND apellidos_normalized = %s
        ''', (first_name_normalized, last_names_normalized))
        existing_guest = cur.fetchone()
        
        if existing_guest:
            logger.warning(f"[{request_id}] ✗ DUPLICATE DETECTED (exact match) - Guest already exists: {existing_guest['nombre']} {existing_guest['apellidos']} (ID: {existing_guest['id']})")
            cur.close()
            conn.close()
            return jsonify({
                'error': 'Este nombre ya ha sido registrado. Si necesitas actualizar tu confirmación, por favor contacta con los novios.'
            }), 409
        
        # Strategy 2: Check for partial last names match (Spanish naming convention)
        # Example: "García López" should match "García" or vice versa
        last_names_parts = last_names_normalized.split()
        if len(last_names_parts) > 0:
            first_last_name = last_names_parts[0]
            
            # Check if someone with same first name and first last name exists
            cur.execute('''
                SELECT id, nombre, apellidos, apellidos_normalized
                FROM guests 
                WHERE nombre_normalized = %s 
                AND (apellidos_normalized = %s 
                     OR apellidos_normalized LIKE %s 
                     OR %s LIKE apellidos_normalized || ' %%')
            ''', (first_name_normalized, first_last_name, first_last_name + ' %', last_names_normalized))
            
            potential_duplicate = cur.fetchone()
            
            if potential_duplicate:
                logger.warning(f"[{request_id}] ✗ POTENTIAL DUPLICATE DETECTED (partial last names match)")
                logger.warning(f"[{request_id}]   New: {guest_data['nombre']} {guest_data['apellidos']} (normalized: {first_name_normalized} {last_names_normalized})")
                logger.warning(f"[{request_id}]   Existing: {potential_duplicate['nombre']} {potential_duplicate['apellidos']} (ID: {potential_duplicate['id']}, normalized: {potential_duplicate['apellidos_normalized']})")
                cur.close()
                conn.close()
                return jsonify({
                    'error': f'Posible duplicado detectado. Ya existe un registro similar: "{potential_duplicate["nombre"]} {potential_duplicate["apellidos"]}". Si eres una persona diferente o necesitas actualizar tu confirmación, por favor contacta con los novios.'
                }), 409
        
        # Insert new guest with both original and normalized names
        cur.execute('''
            INSERT INTO guests (nombre, apellidos, nombre_normalized, apellidos_normalized, 
                              asistencia, acompanado, adultos, ninos, autobus, alergias, comentarios)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, nombre, apellidos, created_at
        ''', (
            guest_data['nombre'],
            guest_data['apellidos'],
            first_name_normalized,
            last_names_normalized,
            guest_data['asistencia'],
            guest_data['acompanado'],
            guest_data['adultos'],
            guest_data['ninos'],
            guest_data['autobus'],
            guest_data['alergias'],
            guest_data['comentarios']
        ))
        
        new_guest = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"[{request_id}] ✓ Guest saved to database - ID: {new_guest['id']}")
        
        # Add to Google Sheets (non-blocking, errors won't fail the request)
        logger.info(f"[{request_id}] Attempting Google Sheets sync...")
        sheets_success = add_to_google_sheets(guest_data)
        
        response_data = {
            'success': True,
            'message': '¡Confirmación recibida con éxito!',
            'guest': {
                'id': new_guest['id'],
                'nombre': new_guest['nombre'],
                'apellidos': new_guest['apellidos'],
                'created_at': new_guest['created_at'].isoformat()
            },
            'synced_to_sheets': sheets_success
        }
        
        logger.info(f"[{request_id}] ✓ SUCCESS - Response: {json_lib.dumps(response_data, ensure_ascii=False)}")
        logger.info(f"[{request_id}] ========================================")
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"[{request_id}] ✗ EXCEPTION - Error creating guest: {str(e)}", exc_info=True)
        logger.info(f"[{request_id}] ========================================")
        return jsonify({
            'error': 'Error al procesar la confirmación. Por favor, inténtalo de nuevo.'
        }), 500

@app.route('/api/guests', methods=['GET'])
def get_guests():
    """Get all guests (optional endpoint for admin purposes)"""
    request_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    logger.info(f"[{request_id}] GET /api/guests - Fetching all guests")
    logger.info(f"[{request_id}] Remote Address: {request.remote_addr}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('SELECT * FROM guests ORDER BY created_at DESC')
        guests = cur.fetchall()
        
        cur.close()
        conn.close()
        
        logger.info(f"[{request_id}] Found {len(guests)} guests in database")
        
        # Convert datetime objects to strings
        for guest in guests:
            if guest['created_at']:
                guest['created_at'] = guest['created_at'].isoformat()
            if guest['updated_at']:
                guest['updated_at'] = guest['updated_at'].isoformat()
        
        logger.info(f"[{request_id}] ✓ Successfully returned {len(guests)} guests")
        
        return jsonify({
            'success': True,
            'count': len(guests),
            'guests': guests
        }), 200
        
    except Exception as e:
        logger.error(f"[{request_id}] ✗ Error fetching guests: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Error al obtener los invitados'
        }), 500

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("🚀 Starting Wedding RSVP Backend API")
    logger.info("=" * 80)
    logger.info(f"Database URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "Database URL: NOT SET")
    logger.info(f"Google Apps Script: {'CONFIGURED' if GOOGLE_APPS_SCRIPT_URL else 'NOT CONFIGURED'}")
    
    # Initialize database on startup
    ensure_database_initialized()
    
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    logger.info("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)
