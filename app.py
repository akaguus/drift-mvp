from flask import Flask, jsonify

from database import init_db
from routes import agents_bp

app = Flask(__name__)

init_db()
app.register_blueprint(agents_bp)


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
