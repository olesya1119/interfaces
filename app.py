from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import math
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


def get_latest_calculation():
    """Получает последний расчет"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith(
            'calculation_') and f.endswith('.json')]
        if not files:
            return None

        # Сортируем по времени создания
        files.sort(key=lambda x: os.path.getctime(
            os.path.join(DATA_DIR, x)), reverse=True)
        latest_file = files[0]

        with open(os.path.join(DATA_DIR, latest_file), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке последнего расчета: {e}")
        return None


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
        # В случае ошибки тоже возвращаем заглушку
        result = generate_stub_result(request.get_json())
        calculation_id = save_calculation_data(
            result.get('result', []),
            result.get('middleValue', 0)
        )

        response_data = result.copy()
        response_data['calculation_id'] = calculation_id

        return jsonify(response_data), 200


def generate_stub_result(data):
    """Генерирует фиктивные данные для тестирования"""
    sample_size = data.get('N', 1000)

    # Генерируем реалистичные данные с нормальным распределением
    mean = random.uniform(10, 50)
    std_dev = random.uniform(5, 15)

    # Генерируем результат как массив размера N
    result_data = []
    for _ in range(sample_size):
        value = random.gauss(mean, std_dev)
        value = max(0.1, value)
        value = min(100, value)
        result_data.append(round(value, 4))

    # Вычисляем среднее значение
    middle_value = sum(result_data) / len(result_data)

    return {
        "result": result_data,
        "middleValue": round(middle_value, 4),
        "stub": True,
        "generated_mean": round(mean, 4),
        "generated_std_dev": round(std_dev, 4),
        "sample_size": sample_size
    }


@app.route("/api/histogram", methods=["GET"])
def get_histogram_data():
    """Возвращает данные для построения гистограммы"""
    try:
        # Получаем последний расчет
        calculation_data = get_latest_calculation()

        if not calculation_data:
            # Если нет сохраненных данных, генерируем тестовые
            test_data = generate_stub_result({"N": 1000})
            calculation_id = save_calculation_data(
                test_data['result'],
                test_data['middleValue']
            )
            calculation_data = {
                'calculation_id': calculation_id,
                'result': test_data['result'],
                'middle_value': test_data['middleValue']
            }

        result_data = calculation_data['result']
        middle_value = calculation_data['middle_value']

        # Формула Стерджеса для начального количества интервалов
        n = len(result_data)
        if n == 0:
            return jsonify({'error': 'Empty data'}), 400

        k_sturges = math.ceil(math.log2(n)) + 1
        k_sturges = max(3, min(k_sturges, 20))

        # Вычисляем границы интервалов
        min_val = min(result_data)
        max_val = max(result_data)
        range_val = max_val - min_val

        # Создаем интервалы по Стерджесу
        bin_edges = []
        bin_width = range_val / k_sturges

        for i in range(k_sturges + 1):
            bin_edges.append(min_val + i * bin_width)

        # Считаем частоты
        frequencies = [0] * k_sturges
        for value in result_data:
            for i in range(k_sturges):
                if bin_edges[i] <= value < bin_edges[i + 1]:
                    frequencies[i] += 1
                    break
            else:
                if value == bin_edges[k_sturges]:
                    frequencies[k_sturges - 1] += 1

        histogram_data = {
            'frequencies': frequencies,
            'bin_edges': bin_edges,
            'bin_centers': [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(k_sturges)],
            'sturges_bins': k_sturges,
            'data_points': n,
            'min_value': min_val,
            'max_value': max_val,
            'middle_value': middle_value,
            'stub_data': True,
            'calculation_id': calculation_data.get('calculation_id', 'unknown')
        }

        return jsonify(histogram_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/histogram/custom", methods=["POST"])
def get_custom_histogram():
    """Гистограмма с пользовательским количеством интервалов"""
    try:
        data = request.get_json()
        custom_bins = data.get('bins', 0)

        # Получаем последний расчет
        calculation_data = get_latest_calculation()

        if not calculation_data:
            return jsonify({'error': 'No data available'}), 400

        result_data = calculation_data['result']
        middle_value = calculation_data['middle_value']

        if custom_bins <= 0:
            return jsonify({'error': 'Invalid number of bins'}), 400

        n = len(result_data)
        k = min(custom_bins, 50)

        # Вычисляем границы интервалов
        min_val = min(result_data)
        max_val = max(result_data)
        range_val = max_val - min_val

        # Создаем интервалы
        bin_edges = []
        bin_width = range_val / k

        for i in range(k + 1):
            bin_edges.append(min_val + i * bin_width)

        # Считаем частоты
        frequencies = [0] * k
        for value in result_data:
            for i in range(k):
                if bin_edges[i] <= value < bin_edges[i + 1]:
                    frequencies[i] += 1
                    break
            else:
                if value == bin_edges[k]:
                    frequencies[k - 1] += 1

        histogram_data = {
            'frequencies': frequencies,
            'bin_edges': bin_edges,
            'bin_centers': [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(k)],
            'custom_bins': k,
            'data_points': n,
            'min_value': min_val,
            'max_value': max_val,
            'middle_value': middle_value,
            'stub_data': True,
            'calculation_id': calculation_data.get('calculation_id', 'unknown')
        }

        return jsonify(histogram_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/test-data", methods=["GET"])
def get_test_data():
    """Endpoint для быстрого тестирования - возвращает готовые данные"""
    test_data = generate_stub_result({"N": 500})
    calculation_id = save_calculation_data(
        test_data['result'],
        test_data['middleValue']
    )

    response_data = test_data.copy()
    response_data['calculation_id'] = calculation_id

    return jsonify(response_data)


@app.route("/api/calculations", methods=["GET"])
def list_calculations():
    """Возвращает список всех расчетов"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith(
            'calculation_') and f.endswith('.json')]
        calculations = []

        for file in files[-10:]:  # Последние 10 расчетов
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

# Очистка старых файлов (опционально)


def cleanup_old_files(max_files=20):
    """Оставляет только последние max_files расчетов"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith(
            'calculation_') and f.endswith('.json')]
        if len(files) > max_files:
            files.sort(key=lambda x: os.path.getctime(
                os.path.join(DATA_DIR, x)))
            for file_to_delete in files[:-max_files]:
                os.remove(os.path.join(DATA_DIR, file_to_delete))
                print(f"Удален старый файл: {file_to_delete}")
    except Exception as e:
        print(f"Ошибка при очистке файлов: {e}")


if __name__ == "__main__":
    # Очищаем старые файлы при запуске
    cleanup_old_files()
    app.run(host='0.0.0.0', port=5000, debug=True)
