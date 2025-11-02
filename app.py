from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import random
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CORS(app)

# Флаг для переключения между реальным Java приложением и заглушкой
USE_JAVA_STUB = True

# Папка для хранения данных
DATA_DIR = "calculation_data"
os.makedirs(DATA_DIR, exist_ok=True)


def save_calculation_data(result_data, middle_value):
    """Сохраняет данные расчета в файл"""
    calculation_id = str(uuid.uuid4())
    filename = f"{DATA_DIR}/calculation_{calculation_id}.json"

    data_to_save = {
        'calculation_id': calculation_id,
        'timestamp': datetime.now().isoformat(),
        'result': result_data,
        'middle_value': middle_value
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    return calculation_id


def load_calculation_data(calculation_id):
    """Загружает данные расчета из файла"""
    filename = f"{DATA_DIR}/calculation_{calculation_id}.json"
    if not os.path.exists(filename):
        return None
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def proxy_calculate():
    """Прокси-эндпоинт для Java приложения или заглушка"""
    try:
        data = request.get_json()
        print("Получены данные для расчета:", data)

        if USE_JAVA_STUB:
            # Используем заглушку
            result = generate_stub_result(data)
            print("Используем заглушку, результат:", result)
        else:
            # Пытаемся подключиться к реальному Java приложению
            java_response = requests.post(
                'http://127.0.0.1:8080/api/calculate',
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            result = java_response.json()
            print("Результат от Java приложения:", result)

        # Сохраняем результат в файл
        calculation_id = save_calculation_data(
            result.get('result', []),
            result.get('middleValue', 0)
        )

        response_data = result.copy()
        response_data['calculation_id'] = calculation_id

        return jsonify(response_data), 200

    except Exception as e:
        print("Ошибка при расчете:", str(e))
        # В случае ошибки при обращении к Java — отвечаем 500
        return jsonify({'error': str(e)}), 500


def generate_stub_result(data):
    """Генерирует фиктивные данные для заглушки расчёта"""
    sample_size = data.get('N', 1000)

    # Генерируем «реалистичные» данные
    mean = random.uniform(10, 50)
    std_dev = random.uniform(5, 15)

    result_data = []
    for _ in range(sample_size):
        # Нормальное распределение с мягкими ограничениями
        value = random.gauss(mean, std_dev)
        value = max(0.1, min(100, value))
        result_data.append(round(value, 4))

    middle_value = sum(result_data) / len(result_data)

    return {
        "result": result_data,
        "middleValue": round(middle_value, 4),
        "stub": True,
        "generated_mean": round(mean, 4),
        "generated_std_dev": round(std_dev, 4),
        "sample_size": sample_size
    }


@app.route("/api/calculations", methods=["GET"])
def list_calculations():
    """Возвращает список всех расчетов (последние 10)"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith('calculation_') and f.endswith('.json')]
        files.sort(key=lambda x: os.path.getctime(os.path.join(DATA_DIR, x)))
        files = files[-10:]

        calculations = []
        for file in files:
            filepath = os.path.join(DATA_DIR, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                calculations.append({
                    'id': data.get('calculation_id'),
                    'timestamp': data.get('timestamp'),
                    'data_points': len(data.get('result', [])),
                    'middle_value': data.get('middle_value')
                })

        return jsonify({'calculations': calculations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/calculation/<calculation_id>", methods=["GET"])
def get_calculation(calculation_id):
    """Возвращает конкретный расчет по ID"""
    calculation_data = load_calculation_data(calculation_id)
    if not calculation_data:
        return jsonify({'error': 'Calculation not found'}), 404
    return jsonify(calculation_data)


def cleanup_old_files(max_files=20):
    """Оставляет только последние max_files расчетов"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith('calculation_') and f.endswith('.json')]
        if len(files) > max_files:
            files.sort(key=lambda x: os.path.getctime(os.path.join(DATA_DIR, x)))
            for file_to_delete in files[:-max_files]:
                os.remove(os.path.join(DATA_DIR, file_to_delete))
                print(f"Удален старый файл: {file_to_delete}")
    except Exception as e:
        print(f"Ошибка при очистке файлов: {e}")


if __name__ == "__main__":
    cleanup_old_files()
    app.run(host='0.0.0.0', port=5000, debug=True)
