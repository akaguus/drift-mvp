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

# Force HTTPS for URL generation in production
app.config['PREFERRED_URL_SCHEME'] = 'https' if FLASK_ENV == 'production' else 'http'

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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
