import os
import json
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode

import requests
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth

# Auth0 configuration
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
AUTH0_BASE_URL = f'https://{AUTH0_DOMAIN}' if AUTH0_DOMAIN else None

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with Flask app"""
    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]):
        print("WARNING: Auth0 environment variables not set. Authentication will be disabled.")
        return None

    try:
        oauth.init_app(app)

        oauth.register(
            'auth0',
            client_id=AUTH0_CLIENT_ID,
            client_secret=AUTH0_CLIENT_SECRET,
            server_metadata_url=f'{AUTH0_BASE_URL}/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid profile email'},
        )
        print(f"✓ OAuth initialized with Auth0 domain: {AUTH0_DOMAIN}")
        return oauth
    except Exception as e:
        print(f"ERROR initializing OAuth: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_current_user():
    """Get currently authenticated user from session"""
    return session.get('user')


def require_auth(f):
    """Decorator to protect routes - requires authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_api_key(f):
    """Decorator for external integrations (Claude/OpenAI) - requires X-API-Key header.
    Resolves the owning user from the key and passes it to the view as `api_user_id`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from database import SessionLocal
        from models import ApiKey

        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'success': False, 'error': 'Missing X-API-Key header'}), 401

        db_session = SessionLocal()
        try:
            key_record = db_session.query(ApiKey).filter(ApiKey.api_key == api_key).first()
            if not key_record:
                return jsonify({'success': False, 'error': 'Invalid API key'}), 401

            key_record.last_used_at = datetime.utcnow()
            db_session.commit()

            kwargs['api_user_id'] = key_record.user_id
            return f(*args, **kwargs)
        finally:
            db_session.close()
    return decorated_function


def get_auth_routes(app, oauth_instance):
    """Register auth routes with Flask app"""

    @app.route('/login')
    def login():
        """Redirect to Auth0 login"""
        if not oauth_instance:
            return jsonify({'error': 'Authentication not configured'}), 500

        try:
            # Build callback URL with correct scheme for production
            callback_url = url_for('callback', _external=True)
            env = os.getenv('FLASK_ENV', 'development')

            # Force HTTPS in production (Railway uses X-Forwarded-Proto)
            if env == 'production':
                callback_url = callback_url.replace('http://', 'https://')

            return oauth_instance.auth0.authorize_redirect(
                redirect_uri=callback_url
            )
        except Exception as e:
            print(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Login failed: {str(e)}'}), 500

    @app.route('/callback')
    def callback():
        """Auth0 callback - user authenticated"""
        if not oauth_instance:
            return jsonify({'error': 'Authentication not configured'}), 500

        try:
            token = oauth_instance.auth0.authorize_access_token()
            user_info = token.get('userinfo')

            if user_info:
                session['user'] = {
                    'user_id': user_info.get('sub'),  # Auth0 unique identifier
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture')
                }
                session.permanent = True

            return redirect(url_for('index'))
        except Exception as e:
            print(f"Auth callback error: {e}")
            return jsonify({'error': 'Authentication failed'}), 400

    @app.route('/logout')
    def logout():
        """Logout user and clear session"""
        session.clear()

        # Redirect to Auth0 logout (optional, but recommended)
        if AUTH0_DOMAIN:
            return_url = url_for('index', _external=True)
            env = os.getenv('FLASK_ENV', 'development')

            # Force HTTPS in production (Railway uses X-Forwarded-Proto)
            if env == 'production':
                return_url = return_url.replace('http://', 'https://')

            logout_url = urlencode({
                'returnTo': return_url,
                'client_id': AUTH0_CLIENT_ID
            })
            return redirect(f'{AUTH0_BASE_URL}/v2/logout?{logout_url}')

        return redirect(url_for('index'))

    @app.route('/api/me')
    @require_auth
    def get_user_profile():
        """Get current user profile"""
        user = get_current_user()
        return jsonify(user), 200

    return {
        'get_current_user': get_current_user,
        'require_auth': require_auth,
    }
