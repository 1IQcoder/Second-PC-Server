"""
Build command (old):
pyinstaller --add-data "templates;templates" --add-data "static;static" --add-data "bats;bats" flask_app.py
"""

import os, sys, webbrowser, threading
import logging as log

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from flask import Flask, render_template
from src.core import Directory
from src.config import CLIENT_DIR
from src.api_router import api_bp
from src.app_router import cf_bp, dk_bp

log.basicConfig(
    level=log.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        log.StreamHandler()
    ]
)

app = Flask(
    __name__,
    static_folder=os.path.join(CLIENT_DIR, "static"),
    template_folder=os.path.join(CLIENT_DIR, "templates")
)

@app.route('/')
def menu():
    return render_template('menu.html')

app.register_blueprint(cf_bp, url_prefix='/cf')
app.register_blueprint(dk_bp, url_prefix='/dk')
app.register_blueprint(api_bp, url_prefix='/api')

def open_browser():
    url = 'http://localhost:1488/cf/config' if not Directory.is_cf_ready() else 'http://localhost:1488/'
    webbrowser.open(url)

if __name__ == "__main__":
    log.info("Starting SecondPCServer...")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=1488)

