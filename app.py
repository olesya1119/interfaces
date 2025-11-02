from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

# Адреса Java-сервиса (переопределяются переменными окружения при желании)
JAVA_API_URL = os.getenv('JAVA_API_URL', 'http://127.0.0.1:8080/api/calculate')
JAVA_SMO_API_URL = os.getenv('JAVA_SMO_API_URL', 'http://127.0.0.1:8080/api/smo/calculate')


@app.route("/", methods=["GET"])
def root():
    return redirect(url_for('step', step_id=1))


@app.route("/step/<int:step_id>", methods=["GET"])
def step(step_id: int):
    if step_id == 1:
        return render_template("routes_step.html", step_id=1, page_title="Маршруты 1ой подтемы")
    elif step_id == 2:
        return render_template("routes_step.html", step_id=2, page_title="Маршруты 2ой подтемы")
    elif step_id == 3:
        return render_template("step3.html")
    else:
        return "Not Found", 404


@app.route("/api/calculate", methods=["POST"])
def proxy_calculate():
    """Прокси в Java /api/calculate"""
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        r = requests.post(JAVA_API_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=15)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to reach Java service', 'details': str(e)}), 502

    ct = (r.headers.get('Content-Type') or '').lower()
    if 'application/json' in ct:
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            return jsonify({'error': 'Invalid JSON from Java service'}), 502
    return Response(r.content, status=r.status_code, mimetype=r.headers.get('Content-Type', 'application/octet-stream'))


@app.route("/api/smo/calculate", methods=["POST"])
def proxy_smo_calculate():
    """Прокси в Java /api/smo/calculate"""
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        r = requests.post(JAVA_SMO_API_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=20)
    except requests.RequestException as e:
        return jsonify({'error': 'Failed to reach Java service', 'details': str(e)}), 502

    # Ответ «просто число» — пробрасываем как есть (text/plain) или JSON
    ct = (r.headers.get('Content-Type') or '').lower()
    if 'application/json' in ct:
        try:
            return jsonify(r.json()), r.status_code
        except ValueError:
            # На случай если Java вернула "12.34" с JSON content-type — отдадим как текст
            return Response(r.text, status=r.status_code, mimetype='text/plain')
    return Response(r.content, status=r.status_code, mimetype=r.headers.get('Content-Type', 'text/plain'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
