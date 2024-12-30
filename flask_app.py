from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


def run_flask():
    app.run(host="0.0.0.0", port=5000)
