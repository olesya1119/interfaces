from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        # Получаем данные из формы
        probabilities = request.form.getlist("route_prob")
        sample_size = request.form.get("sample_size")
        action_times = request.form.getlist("time_value")
        error_probs = request.form.getlist("error_prob")
        error_actions = request.form.getlist("error_action")

        # Здесь можно обработать данные (пока просто показываем обратно)
        result = {
            "probabilities": probabilities,
            "sample_size": sample_size,
            "action_times": action_times,
            "error_probs": error_probs,
            "error_actions": error_actions
        }

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)
