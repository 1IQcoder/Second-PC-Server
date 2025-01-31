import os, sys, logging

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from src.flask_app import run_flask

if __name__ == "__main__":
    logging.info("Starting Flask application...")
    run_flask()
