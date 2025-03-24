"""
Build command:
    pyinstaller --add-data "../core;core" --distpath ../../build/ --workpath ../../build/trash/ --hidden-import=requests --clean -y server.py
"""

import os, webbrowser, threading
import logging as log

from flask import Flask, render_template
from core import AppDir, APP_DIR
# from src.api_router import api_bp
from app_router import cf_bp, dk_bp

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
    static_folder=os.path.join(APP_DIR, 'client', 'static'),
    template_folder=os.path.join(APP_DIR, 'client', 'templates')
)

@app.route('/')
def menu():
    return render_template('menu.html')

app.register_blueprint(cf_bp, url_prefix='/cf')
app.register_blueprint(dk_bp, url_prefix='/dk')
# app.register_blueprint(api_bp, url_prefix='/api')

def open_browser():
    url = 'http://localhost:1488/cf/config' if not AppDir.is_cf_ready() else 'http://localhost:1488/'
    webbrowser.open(url)

if __name__ == "__main__":
    AppDir.create_db_folder()
    log.info("Starting SecondPCServer...")
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=1488)

