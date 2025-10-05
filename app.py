from flask import Flask, render_template, request, jsonify
import requests
from flask_cors import CORS  # добавьте эту строку

app = Flask(__name__)
CORS(app)  # добавьте эту строку


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def proxy_calculate():
    """Прокси-эндпоинт для Java приложения"""
    try:
        # Получаем данные из запроса
        data = request.get_json()

        # Отправляем запрос к Java приложению
        java_response = requests.post(
            'http://127.0.0.1:8080/api/calculate',
            json=data,
            headers={'Content-Type': 'application/json'}
        )

        # Возвращаем ответ от Java приложения
        return jsonify(java_response.json()), java_response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
