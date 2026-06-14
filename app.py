import os

from flask import Flask, jsonify, send_from_directory

from database import init_db
from routes import agents_bp
from scheduler import Scheduler
import scheduler as scheduler_module

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Production settings
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
app.config['ENV'] = FLASK_ENV
app.config['DEBUG'] = FLASK_ENV != 'production'

init_db()
app.register_blueprint(agents_bp)

scheduler = Scheduler()
scheduler_module._scheduler_instance = scheduler
scheduler.start()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
