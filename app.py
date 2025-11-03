from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import requests
import os
import logging
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

# Логи
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger('api')

def trunc500(s: str) -> str:
    return s if len(s) <= 500 else s[:500] + '…'

# Адреса Java-сервиса
JAVA_API_URL = os.getenv('JAVA_API_URL', 'http://127.0.0.1:8080/api/calculate')
JAVA_SMO_API_URL = os.getenv('JAVA_SMO_API_URL', 'http://127.0.0.1:8080/api/smo/calculate')

@app.get("/")
def tabs():
    return render_template("tabs.html")

@app.post("/api/calculate")
def proxy_calculate():
    """Прокси в Java /api/calculate"""
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        logger.info(f"{request.path} payload={trunc500(json.dumps(payload, ensure_ascii=False))}")
        r = requests.post(JAVA_API_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
        logger.info(f"{request.path} -> status={r.status_code}")
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to reach Java service', 'details': str(e)}), 502

    ct = (r.headers.get('Content-Type') or '').lower()
    if 'application/json' in ct:
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            return jsonify({'error': 'Invalid JSON from Java service'}), 502
    return Response(r.content, status=r.status_code, mimetype=r.headers.get('Content-Type', 'application/octet-stream'))

@app.post("/api/smo/calculate")
def proxy_smo_calculate():
    """Прокси в Java /api/smo/calculate"""
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        logger.info(f"{request.path} payload={trunc500(json.dumps(payload, ensure_ascii=False))}")
        r = requests.post(JAVA_SMO_API_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=20)
        logger.info(f"{request.path} -> status={r.status_code}")
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to reach Java service', 'details': str(e)}), 502

    ct = (r.headers.get('Content-Type') or '').lower()
    if 'application/json' in ct:
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            return Response(r.text, status=r.status_code, mimetype='text/plain')
    return Response(r.content, status=r.status_code, mimetype=r.headers.get('Content-Type', 'text/plain'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
