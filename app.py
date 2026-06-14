from flask import Flask, jsonify

from database import init_db

app = Flask(__name__)

init_db()


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
