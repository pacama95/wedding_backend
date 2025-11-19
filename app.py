import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import or_, literal
from sqlalchemy.exc import IntegrityError
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

db = SQLAlchemy()
migrate = Migrate()

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    logger.warning("⚠️  DATABASE_URL not set - defaulting to in-memory SQLite (data will not persist)")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate.init_app(app, db)

# Google Sheets configuration
GOOGLE_APPS_SCRIPT_URL = os.environ.get('GOOGLE_APPS_SCRIPT_URL')

def run_migrations_on_startup():
    if not DATABASE_URL:
        logger.warning("⚠️  DATABASE_URL not set - cannot run migrations")
        return

    from flask_migrate import upgrade as migrate_upgrade

    try:
        with app.app_context():
            logger.info("Running database migrations...")
            migrate_upgrade()
            logger.info("✓ Database migrations applied")
    except Exception as e:
        logger.error(f"✗ Failed to run database migrations: {str(e)}", exc_info=True)

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

class Guest(db.Model):
    __tablename__ = 'guests'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    apellidos = db.Column(db.String(255), nullable=False)
    nombre_normalized = db.Column(db.String(255), nullable=False)
    apellidos_normalized = db.Column(db.String(255), nullable=False)
    asistencia = db.Column(db.String(50), nullable=False)
    acompanado = db.Column(db.String(10), nullable=False)
    adultos = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    ninos = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    autobus = db.Column(db.String(50))
    alergias = db.Column(db.Text)
    comentarios = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('nombre_normalized', 'apellidos_normalized', name='uix_guests_normalized_names'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellidos': self.apellidos,
            'nombre_normalized': self.nombre_normalized,
            'apellidos_normalized': self.apellidos_normalized,
            'asistencia': self.asistencia,
            'acompanado': self.acompanado,
            'adultos': self.adultos,
            'ninos': self.ninos,
            'autobus': self.autobus,
            'alergias': self.alergias,
            'comentarios': self.comentarios,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

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
        
        # Check if guest already exists with multiple strategies
        logger.debug(f"[{request_id}] Checking for duplicate...")

        existing_guest = Guest.query.filter_by(
            nombre_normalized=first_name_normalized,
            apellidos_normalized=last_names_normalized
        ).first()

        if existing_guest:
            logger.warning(f"[{request_id}] ✗ DUPLICATE DETECTED (exact match) - Guest already exists: {existing_guest.nombre} {existing_guest.apellidos} (ID: {existing_guest.id})")
            return jsonify({
                'error': 'Este nombre ya ha sido registrado. Si necesitas actualizar tu confirmación, por favor contacta con los novios.'
            }), 409

        # Strategy 2: Check for partial last names match (Spanish naming convention)
        potential_duplicate = None
        last_names_parts = last_names_normalized.split()
        if last_names_parts:
            first_last_name = last_names_parts[0]
            potential_duplicate = (
                Guest.query
                .filter(Guest.nombre_normalized == first_name_normalized)
                .filter(
                    or_(
                        Guest.apellidos_normalized == first_last_name,
                        Guest.apellidos_normalized.like(f"{first_last_name} %"),
                        literal(last_names_normalized).like(db.func.concat(Guest.apellidos_normalized, ' %'))
                    )
                )
                .first()
            )

        if potential_duplicate:
            logger.warning(f"[{request_id}] ✗ POTENTIAL DUPLICATE DETECTED (partial last names match)")
            logger.warning(f"[{request_id}]   New: {guest_data['nombre']} {guest_data['apellidos']} (normalized: {first_name_normalized} {last_names_normalized})")
            logger.warning(f"[{request_id}]   Existing: {potential_duplicate.nombre} {potential_duplicate.apellidos} (ID: {potential_duplicate.id}, normalized: {potential_duplicate.apellidos_normalized})")
            return jsonify({
                'error': f'Posible duplicado detectado. Ya existe un registro similar: "{potential_duplicate.nombre} {potential_duplicate.apellidos}". Si eres una persona diferente o necesitas actualizar tu confirmación, por favor contacta con los novios.'
            }), 409

        new_guest = Guest(
            nombre=guest_data['nombre'],
            apellidos=guest_data['apellidos'],
            nombre_normalized=first_name_normalized,
            apellidos_normalized=last_names_normalized,
            asistencia=guest_data['asistencia'],
            acompanado=guest_data['acompanado'],
            adultos=guest_data['adultos'],
            ninos=guest_data['ninos'],
            autobus=guest_data['autobus'],
            alergias=guest_data['alergias'],
            comentarios=guest_data['comentarios']
        )

        db.session.add(new_guest)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            logger.warning(f"[{request_id}] ✗ DUPLICATE DETECTED (db constraint) - Guest already exists")
            return jsonify({
                'error': 'Este nombre ya ha sido registrado. Si necesitas actualizar tu confirmación, por favor contacta con los novios.'
            }), 409
        
        logger.info(f"[{request_id}] ✓ Guest saved to database - ID: {new_guest.id}")
        
        # Add to Google Sheets (non-blocking, errors won't fail the request)
        logger.info(f"[{request_id}] Attempting Google Sheets sync...")
        sheets_success = add_to_google_sheets(guest_data)
        
        response_data = {
            'success': True,
            'message': '¡Confirmación recibida con éxito!',
            'guest': {
                'id': new_guest.id,
                'nombre': new_guest.nombre,
                'apellidos': new_guest.apellidos,
                'created_at': new_guest.created_at.isoformat() if new_guest.created_at else None
            },
            'synced_to_sheets': sheets_success
        }
        
        logger.info(f"[{request_id}] ✓ SUCCESS - Response: {json_lib.dumps(response_data, ensure_ascii=False)}")
        logger.info(f"[{request_id}] ========================================")
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
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
        guests = Guest.query.order_by(Guest.created_at.desc()).all()
        guests_payload = [guest.to_dict() for guest in guests]
        
        logger.info(f"[{request_id}] Found {len(guests_payload)} guests in database")
        
        logger.info(f"[{request_id}] ✓ Successfully returned {len(guests)} guests")
        
        return jsonify({
            'success': True,
            'count': len(guests_payload),
            'guests': guests_payload
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
    
    # Apply database migrations on startup
    run_migrations_on_startup()
    
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on 0.0.0.0:{port}")
    logger.info("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)
