import os
import logging
from datetime import timedelta

from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv

from database import init_db
from routes import agents_bp
from scheduler import Scheduler
from auth import init_oauth, get_auth_routes
import scheduler as scheduler_module

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Production settings
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
app.config['ENV'] = FLASK_ENV
app.config['DEBUG'] = FLASK_ENV != 'production'

# Session configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = FLASK_ENV == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize OAuth/Auth0
oauth = init_oauth(app)

# Register auth routes
auth_funcs = get_auth_routes(app, oauth)

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

app.register_blueprint(agents_bp)

# Initialize scheduler with error handling
try:
    scheduler = Scheduler()
    scheduler_module._scheduler_instance = scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/debug/auth-config')
def debug_auth_config():
    """Debug endpoint - shows if Auth0 is configured"""
    return jsonify({
        'auth0_domain_set': bool(os.getenv('AUTH0_DOMAIN')),
        'auth0_client_id_set': bool(os.getenv('AUTH0_CLIENT_ID')),
        'auth0_client_secret_set': bool(os.getenv('AUTH0_CLIENT_SECRET')),
        'secret_key_set': bool(os.getenv('SECRET_KEY')),
        'flask_env': os.getenv('FLASK_ENV', 'development'),
        'oauth_initialized': oauth is not None
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
